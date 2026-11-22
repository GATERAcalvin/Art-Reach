# ArtReach

A menu-driven command-line application that gives artists **visibility** and
connects them with **opportunities** (exhibitions, concerts, festivals,
workshops, open calls, residencies, grants). Organizers post opportunities,
review applicants and invite artists; artists build a public profile, apply and
track their reach.

Built for the Peer Learning Project (BSE Year 1, Trimester 2) with Python 3 and
SQLite. It uses only the standard library, so there is nothing to install.

## Run it

```bash
python3 seed.py     # optional: load demo data (password for all: demo1234)
python3 main.py     # start the app
python3 -m unittest discover -s tests -t .   # run the tests
```

Demo logins: `aline@demo.rw` (artist), `hub@demo.rw` (organizer).
The database file `artreach.db` is created next to `main.py`
(override with the `ARTREACH_DB` environment variable).

## Requirements

| # | Requirement |
|---|-------------|
| 1 | Users register as **artist** or **organizer** and log in with a hashed password (PBKDF2). |
| 2 | Anyone can browse open opportunities and the artist showcase without an account. |
| 3 | Organizers post, close/reopen and delete opportunities; deadline cannot be after the event date. |
| 4 | Artists search by discipline, type, city and keyword, then apply with a message (one application per opportunity). |
| 5 | Organizers accept or reject applicants; an opportunity closes automatically when all spots are filled. |
| 6 | Organizers can search artists and send invitations; artists accept or decline (accepting creates an accepted application). |
| 7 | Viewing an artist profile increases their `profile_views`, shown on their dashboard (visibility). |
| 8 | Artists can withdraw pending applications and edit their profile. |
| 9 | Bad input never crashes the app: prompts repeat until valid, rule violations show a message. |

## Design

* `artreach/database.py` - schema and every SQL query (`Database` class).
  Rule violations raise `ArtReachError`.
* `artreach/utils.py` - validated input helpers and table printing.
* `artreach/app.py` - main menu, registration, login.
* `artreach/artist_menu.py`, `artreach/organizer_menu.py`, `artreach/views.py` - screens.
* `seed.py` - demo data. `tests/` - unit tests on an in-memory database.

### Tables

```
users(user_id PK, name, email UNIQUE, password_hash, role, city, discipline,
      bio, portfolio_url, profile_views, created_at)
events(event_id PK, organizer_id FK, title, description, event_type, discipline,
       city, event_date, deadline, compensation, spots, status, created_at)
applications(application_id PK, event_id FK, artist_id FK, message, status,
             applied_at, UNIQUE(event_id, artist_id))
invitations(invitation_id PK, event_id FK, artist_id FK, message, status,
            sent_at, UNIQUE(event_id, artist_id))
```

Foreign keys are enforced (`PRAGMA foreign_keys = ON`) and deleting an event or
user cascades to its applications and invitations. `CHECK` constraints protect
roles, statuses, spot counts and dates.

## Concepts used

`while` loops (menus and input validation), conditionals, functions and classes,
`try`/`except` (including `KeyboardInterrupt` and `EOFError` for Ctrl+C / Ctrl+D),
parameterised SQL (no injection), joins, aggregates, and unit tests.
