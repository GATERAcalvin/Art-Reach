"""SQLite storage layer for ArtReach.

All SQL lives in the Database class. Business rule problems (duplicate
application, closed event, wrong owner...) raise ArtReachError so the menus can
show a friendly message instead of crashing.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import date

DEFAULT_DB_PATH = os.environ.get(
    "ARTREACH_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "artreach.db"),
)

DISCIPLINES = ["Visual Art", "Music", "Dance", "Theatre", "Film",
               "Photography", "Poetry & Spoken Word", "Fashion", "Crafts",
               "Other"]
EVENT_TYPES = ["Exhibition", "Concert", "Festival", "Workshop", "Open Call",
               "Residency", "Grant / Competition", "Market / Fair"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('artist', 'organizer')),
    city          TEXT,
    discipline    TEXT,
    bio           TEXT,
    portfolio_url TEXT,
    profile_views INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    organizer_id INTEGER NOT NULL
                 REFERENCES users (user_id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    description  TEXT,
    event_type   TEXT NOT NULL,
    discipline   TEXT NOT NULL,
    city         TEXT NOT NULL,
    event_date   TEXT NOT NULL,
    deadline     TEXT NOT NULL,
    compensation TEXT,
    spots        INTEGER NOT NULL CHECK (spots > 0),
    status       TEXT NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open', 'closed')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (deadline <= event_date)
);

CREATE TABLE IF NOT EXISTS applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id       INTEGER NOT NULL
                   REFERENCES events (event_id) ON DELETE CASCADE,
    artist_id      INTEGER NOT NULL
                   REFERENCES users (user_id) ON DELETE CASCADE,
    message        TEXT,
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'accepted', 'rejected')),
    applied_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (event_id, artist_id)
);

CREATE TABLE IF NOT EXISTS invitations (
    invitation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL
                  REFERENCES events (event_id) ON DELETE CASCADE,
    artist_id     INTEGER NOT NULL
                  REFERENCES users (user_id) ON DELETE CASCADE,
    message       TEXT,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'accepted', 'declined')),
    sent_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (event_id, artist_id)
);

CREATE INDEX IF NOT EXISTS idx_events_city ON events (city);
CREATE INDEX IF NOT EXISTS idx_events_discipline ON events (discipline);
"""

# Shared SELECT used wherever an event is listed.
EVENT_SELECT = """
SELECT e.*, u.name AS organizer_name,
       e.spots - (SELECT COUNT(*) FROM applications a
                  WHERE a.event_id = e.event_id
                    AND a.status = 'accepted') AS spots_left
FROM events e JOIN users u ON u.user_id = e.organizer_id
"""


class ArtReachError(Exception):
    """A rule of the app was broken (shown to the user, not a crash)."""


def hash_password(password, salt=None):
    """Return 'salt$hash' using PBKDF2-HMAC-SHA256."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def check_password(password, stored):
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def today():
    return date.today().isoformat()


class Database:
    """Everything the app needs to read and write."""

    def __init__(self, path=None):
        self.conn = sqlite3.connect(path or DEFAULT_DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ------------------------------------------------------------ users
    def create_user(self, name, email, password, role, city="",
                    discipline="", bio="", portfolio_url=""):
        if role not in ("artist", "organizer"):
            raise ArtReachError("Role must be artist or organizer.")
        try:
            cur = self.conn.execute(
                "INSERT INTO users (name, email, password_hash, role, city, "
                "discipline, bio, portfolio_url) VALUES (?,?,?,?,?,?,?,?)",
                (name, email.strip(), hash_password(password), role, city,
                 discipline, bio, portfolio_url))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ArtReachError("That email is already registered.")
        return cur.lastrowid

    def authenticate(self, email, password):
        row = self.conn.execute("SELECT * FROM users WHERE email = ?",
                                (email.strip(),)).fetchone()
        if row and check_password(password, row["password_hash"]):
            return row
        return None

    def get_user(self, user_id):
        return self.conn.execute("SELECT * FROM users WHERE user_id = ?",
                                 (user_id,)).fetchone()

    def update_profile(self, user_id, **fields):
        allowed = {"name", "city", "discipline", "bio", "portfolio_url"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        assignments = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE users SET {assignments} WHERE user_id = ?",
                          (*fields.values(), user_id))
        self.conn.commit()

    def list_artists(self, discipline=None, city=None, keyword=None):
        sql = "SELECT * FROM users WHERE role = 'artist'"
        params = []
        if discipline:
            sql += " AND discipline = ?"
            params.append(discipline)
        if city:
            sql += " AND city LIKE ?"
            params.append(f"%{city}%")
        if keyword:
            sql += " AND (name LIKE ? OR bio LIKE ?)"
            params += [f"%{keyword}%"] * 2
        sql += " ORDER BY profile_views DESC, name"
        return self.conn.execute(sql, params).fetchall()

    def view_artist(self, artist_id):
        """Open an artist's profile; each view counts toward visibility."""
        artist = self.conn.execute(
            "SELECT * FROM users WHERE user_id = ? AND role = 'artist'",
            (artist_id,)).fetchone()
        if artist is None:
            raise ArtReachError("No artist with that ID.")
        self.conn.execute("UPDATE users SET profile_views = profile_views + 1 "
                          "WHERE user_id = ?", (artist_id,))
        self.conn.commit()
        return self.get_user(artist_id)

    # ----------------------------------------------------------- events
    def create_event(self, organizer_id, title, description, event_type,
                     discipline, city, event_date, deadline, compensation,
                     spots):
        if deadline > event_date:
            raise ArtReachError("The deadline cannot be after the event date.")
        try:
            cur = self.conn.execute(
                "INSERT INTO events (organizer_id, title, description, "
                "event_type, discipline, city, event_date, deadline, "
                "compensation, spots) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (organizer_id, title, description, event_type, discipline,
                 city, event_date, deadline, compensation, spots))
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ArtReachError(f"Could not save the event: {exc}")
        return cur.lastrowid

    def get_event(self, event_id):
        return self.conn.execute(EVENT_SELECT + " WHERE e.event_id = ?",
                                 (event_id,)).fetchone()

    def list_events(self, discipline=None, city=None, event_type=None,
                    keyword=None, include_closed=False):
        sql = EVENT_SELECT + " WHERE 1 = 1"
        params = []
        if not include_closed:
            sql += " AND e.status = 'open' AND e.deadline >= ?"
            params.append(today())
        if discipline:
            sql += " AND e.discipline = ?"
            params.append(discipline)
        if city:
            sql += " AND e.city LIKE ?"
            params.append(f"%{city}%")
        if event_type:
            sql += " AND e.event_type = ?"
            params.append(event_type)
        if keyword:
            sql += " AND (e.title LIKE ? OR e.description LIKE ?)"
            params += [f"%{keyword}%"] * 2
        sql += " ORDER BY e.deadline, e.event_id"
        return self.conn.execute(sql, params).fetchall()

    def events_by_organizer(self, organizer_id):
        return self.conn.execute(
            EVENT_SELECT + " WHERE e.organizer_id = ? "
            "ORDER BY e.event_date DESC", (organizer_id,)).fetchall()

    def _owned_event(self, event_id, organizer_id):
        event = self.get_event(event_id)
        if event is None or event["organizer_id"] != organizer_id:
            raise ArtReachError("You have no event with that ID.")
        return event

    def set_event_status(self, event_id, organizer_id, status):
        if status not in ("open", "closed"):
            raise ArtReachError("Status must be open or closed.")
        event = self._owned_event(event_id, organizer_id)
        if status == "open" and event["spots_left"] <= 0:
            raise ArtReachError("All spots are filled, so it cannot reopen.")
        self.conn.execute("UPDATE events SET status = ? WHERE event_id = ?",
                          (status, event_id))
        self.conn.commit()

    def delete_event(self, event_id, organizer_id):
        """Delete an event. Its applications and invitations go with it."""
        self._owned_event(event_id, organizer_id)
        self.conn.execute("DELETE FROM events WHERE event_id = ?",
                          (event_id,))
        self.conn.commit()

    # ----------------------------------------------------- applications
    def _require_open(self, event):
        if event is None:
            raise ArtReachError("No event with that ID.")
        if event["status"] != "open" or event["deadline"] < today():
            raise ArtReachError("This opportunity is closed.")
        if event["spots_left"] <= 0:
            raise ArtReachError("All spots are filled.")

    def apply(self, event_id, artist_id, message=""):
        event = self.get_event(event_id)
        self._require_open(event)
        try:
            cur = self.conn.execute(
                "INSERT INTO applications (event_id, artist_id, message) "
                "VALUES (?,?,?)", (event_id, artist_id, message))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ArtReachError("You already applied to this opportunity.")
        return cur.lastrowid

    def applications_for_artist(self, artist_id):
        return self.conn.execute(
            "SELECT a.*, e.title, e.event_date, e.city, "
            "u.name AS organizer_name FROM applications a "
            "JOIN events e ON e.event_id = a.event_id "
            "JOIN users u ON u.user_id = e.organizer_id "
            "WHERE a.artist_id = ? ORDER BY a.applied_at DESC",
            (artist_id,)).fetchall()

    def withdraw_application(self, application_id, artist_id):
        row = self.conn.execute(
            "SELECT * FROM applications WHERE application_id = ? "
            "AND artist_id = ?", (application_id, artist_id)).fetchone()
        if row is None:
            raise ArtReachError("You have no application with that ID.")
        if row["status"] != "pending":
            raise ArtReachError("Only pending applications can be withdrawn.")
        self.conn.execute("DELETE FROM applications WHERE application_id = ?",
                          (application_id,))
        self.conn.commit()

    def applications_for_event(self, event_id, organizer_id):
        self._owned_event(event_id, organizer_id)
        return self.conn.execute(
            "SELECT a.*, u.name AS artist_name, u.discipline, u.city, "
            "u.portfolio_url FROM applications a "
            "JOIN users u ON u.user_id = a.artist_id "
            "WHERE a.event_id = ? ORDER BY a.applied_at", (event_id,)
        ).fetchall()

    def decide_application(self, application_id, organizer_id, status):
        if status not in ("accepted", "rejected"):
            raise ArtReachError("Decision must be accepted or rejected.")
        row = self.conn.execute(
            "SELECT a.*, e.organizer_id FROM applications a "
            "JOIN events e ON e.event_id = a.event_id "
            "WHERE a.application_id = ?", (application_id,)).fetchone()
        if row is None or row["organizer_id"] != organizer_id:
            raise ArtReachError("That application is not for your events.")
        if status == "accepted" and row["status"] != "accepted":
            event = self.get_event(row["event_id"])
            if event["spots_left"] <= 0:
                raise ArtReachError("All spots are already filled.")
        self.conn.execute("UPDATE applications SET status = ? "
                          "WHERE application_id = ?", (status, application_id))
        # Close the event automatically once its last spot is taken.
        event = self.get_event(row["event_id"])
        if event["spots_left"] <= 0 and event["status"] == "open":
            self.conn.execute("UPDATE events SET status = 'closed' "
                              "WHERE event_id = ?", (row["event_id"],))
        self.conn.commit()

    # ------------------------------------------------------ invitations
    def invite(self, event_id, organizer_id, artist_id, message=""):
        event = self._owned_event(event_id, organizer_id)
        self._require_open(event)
        artist = self.conn.execute(
            "SELECT 1 FROM users WHERE user_id = ? AND role = 'artist'",
            (artist_id,)).fetchone()
        if artist is None:
            raise ArtReachError("No artist with that ID.")
        try:
            cur = self.conn.execute(
                "INSERT INTO invitations (event_id, artist_id, message) "
                "VALUES (?,?,?)", (event_id, artist_id, message))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ArtReachError("That artist was already invited.")
        return cur.lastrowid

    def invitations_for_artist(self, artist_id):
        return self.conn.execute(
            "SELECT i.*, e.title, e.event_date, e.city, e.deadline, "
            "u.name AS organizer_name FROM invitations i "
            "JOIN events e ON e.event_id = i.event_id "
            "JOIN users u ON u.user_id = e.organizer_id "
            "WHERE i.artist_id = ? ORDER BY i.sent_at DESC",
            (artist_id,)).fetchall()

    def respond_invitation(self, invitation_id, artist_id, accept):
        inv = self.conn.execute(
            "SELECT * FROM invitations WHERE invitation_id = ? "
            "AND artist_id = ?", (invitation_id, artist_id)).fetchone()
        if inv is None:
            raise ArtReachError("You have no invitation with that ID.")
        if inv["status"] != "pending":
            raise ArtReachError("You already answered this invitation.")
        if accept:
            event = self.get_event(inv["event_id"])
            self._require_open(event)
            existing = self.conn.execute(
                "SELECT application_id FROM applications WHERE event_id = ? "
                "AND artist_id = ?", (inv["event_id"], artist_id)).fetchone()
            if existing:
                self.conn.execute("UPDATE applications SET status = 'accepted'"
                                  " WHERE application_id = ?",
                                  (existing["application_id"],))
            else:
                self.conn.execute(
                    "INSERT INTO applications (event_id, artist_id, message, "
                    "status) VALUES (?,?,?, 'accepted')",
                    (inv["event_id"], artist_id, "Accepted an invitation"))
        self.conn.execute("UPDATE invitations SET status = ? "
                          "WHERE invitation_id = ?",
                          ("accepted" if accept else "declined",
                           invitation_id))
        event = self.get_event(inv["event_id"])
        if event["spots_left"] <= 0 and event["status"] == "open":
            self.conn.execute("UPDATE events SET status = 'closed' "
                              "WHERE event_id = ?", (inv["event_id"],))
        self.conn.commit()

    # -------------------------------------------------------- dashboards
    def artist_stats(self, artist_id):
        count = lambda table, status: self.conn.execute(  # noqa: E731
            f"SELECT COUNT(*) FROM {table} WHERE artist_id = ? AND status = ?",
            (artist_id, status)).fetchone()[0]
        return {
            "profile_views": self.get_user(artist_id)["profile_views"],
            "pending": count("applications", "pending"),
            "accepted": count("applications", "accepted"),
            "rejected": count("applications", "rejected"),
            "invitations": count("invitations", "pending"),
        }

    def organizer_stats(self, organizer_id):
        one = lambda sql: self.conn.execute(  # noqa: E731
            sql, (organizer_id,)).fetchone()[0]
        return {
            "events": one("SELECT COUNT(*) FROM events "
                          "WHERE organizer_id = ?"),
            "open_events": one("SELECT COUNT(*) FROM events "
                               "WHERE organizer_id = ? AND status = 'open'"),
            "applications": one(
                "SELECT COUNT(*) FROM applications a JOIN events e "
                "ON e.event_id = a.event_id WHERE e.organizer_id = ?"),
            "pending": one(
                "SELECT COUNT(*) FROM applications a JOIN events e "
                "ON e.event_id = a.event_id WHERE e.organizer_id = ? "
                "AND a.status = 'pending'"),
        }
