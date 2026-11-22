"""Entry point logic: guest menu, registration and login."""
from . import artist_menu, organizer_menu
from .database import ArtReachError, DISCIPLINES, Database
from .utils import (ask, ask_choice, ask_email, ask_password, banner, menu,
                    pause)
from .views import browse_artists, browse_events


def register(db):
    banner("Create an account")
    print("I am joining as:")
    role = ask_choice("Choose", ["artist", "organizer"])
    name = ask("Full name" if role == "artist" else "Name of you / your group")
    email = ask_email()
    password = ask_password("Password (min 6 characters)", confirm=True)
    city = ask("City", required=False)
    discipline = bio = link = ""
    if role == "artist":
        print("Your main discipline:")
        discipline = ask_choice("Choose", DISCIPLINES)
        bio = ask("Short bio", required=False)
        link = ask("Portfolio link (optional)", required=False)
    db.create_user(name, email, password, role, city, discipline, bio, link)
    print("\n  Account created. You can log in now.")
    pause()


def login(db):
    banner("Log in")
    for attempt in range(3):
        email = ask("Email")
        password = ask_password()
        user = db.authenticate(email, password)
        if user:
            return user
        print("  Wrong email or password.")
    print("  Too many failed attempts.")
    pause()
    return None


def main(db_path=None):
    db = Database(db_path)
    try:
        while True:
            choice = menu("ArtReach - visibility and opportunities for artists",
                          [(1, "Log in"), (2, "Create an account"),
                           (3, "Browse open opportunities"),
                           (4, "Artist showcase"), (0, "Exit")])
            try:
                if choice == "1":
                    user = login(db)
                    if user and user["role"] == "artist":
                        artist_menu.run(db, user)
                    elif user:
                        organizer_menu.run(db, user)
                elif choice == "2":
                    register(db)
                elif choice == "3":
                    browse_events(db)
                elif choice == "4":
                    browse_artists(db)
                else:
                    print("Goodbye!")
                    return
            except ArtReachError as err:
                print(f"\n  ! {err}")
                pause()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
    finally:
        db.close()
