"""Fill the database with demo data:  python3 seed.py
Every demo account uses the password: demo1234
"""
import os
import sys
from datetime import date, timedelta

from artreach.database import DEFAULT_DB_PATH, ArtReachError, Database

PASSWORD = "demo1234"


def day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def seed(db):
    artists = [
        ("Aline Uwase", "aline@demo.rw", "Kigali", "Visual Art",
         "Painter exploring memory and everyday Kigali life.",
         "https://example.com/aline"),
        ("Eric Mugisha", "eric@demo.rw", "Kigali", "Music",
         "Afro-fusion guitarist and songwriter.", ""),
        ("Grace Ingabire", "grace@demo.rw", "Huye", "Dance",
         "Contemporary and Intore dance choreographer.", ""),
        ("Patrick Niyonzima", "patrick@demo.rw", "Musanze", "Photography",
         "Documentary photographer of mountain communities.", ""),
        ("Divine Keza", "divine@demo.rw", "Kigali", "Poetry & Spoken Word",
         "Spoken word artist, two-time slam finalist.", ""),
    ]
    organizers = [
        ("Kigali Arts Hub", "hub@demo.rw", "Kigali"),
        ("Inzovu Festival", "inzovu@demo.rw", "Musanze"),
    ]
    ids = {}
    try:
        for name, email, city, disc, bio, link in artists:
            ids[email] = db.create_user(name, email, PASSWORD, "artist", city,
                                        disc, bio, link)
        for name, email, city in organizers:
            ids[email] = db.create_user(name, email, PASSWORD, "organizer",
                                        city)
    except ArtReachError:
        print("Demo data already present, skipping.")
        return
    hub, fest = ids["hub@demo.rw"], ids["inzovu@demo.rw"]
    events = [
        (hub, "Emerging Painters Exhibition", "Group show for new painters.",
         "Exhibition", "Visual Art", "Kigali", day(40), day(20),
         "Free wall space, 30% sales commission waived", 8),
        (hub, "Friday Live Sessions", "Paid live sets at our courtyard.",
         "Concert", "Music", "Kigali", day(25), day(10), "80,000 RWF", 3),
        (fest, "Inzovu Dance Showcase", "Open call for dance groups.",
         "Festival", "Dance", "Musanze", day(60), day(30),
         "Travel + accommodation covered", 4),
        (fest, "Photo Walk Workshop", "Lead a workshop for 20 students.",
         "Workshop", "Photography", "Musanze", day(35), day(15),
         "60,000 RWF", 1),
        (hub, "Spoken Word Night", "Open mic with featured slots.",
         "Open Call", "Poetry & Spoken Word", "Kigali", day(18), day(5),
         "Stipend + meal", 5),
    ]
    event_ids = [db.create_event(*e) for e in events]
    db.apply(event_ids[0], ids["aline@demo.rw"], "I would love to show my series.")
    db.apply(event_ids[1], ids["eric@demo.rw"], "Available every Friday.")
    db.apply(event_ids[4], ids["divine@demo.rw"], "Happy to feature.")
    db.invite(event_ids[2], fest, ids["grace@demo.rw"], "Your work fits us.")
    for artist in ("aline@demo.rw", "eric@demo.rw", "grace@demo.rw"):
        db.view_artist(ids[artist])
    print("Demo data loaded. Log in with e.g. aline@demo.rw (artist) or "
          f"hub@demo.rw (organizer), password {PASSWORD}.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    database = Database(path)
    seed(database)
    database.close()
