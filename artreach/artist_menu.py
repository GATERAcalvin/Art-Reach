"""Menu for logged-in artists."""
from .database import ArtReachError, DISCIPLINES
from .utils import (ask, ask_choice, ask_int, ask_yes_no, banner, menu, pause,
                    show_table)
from .views import browse_artists, browse_events, print_artist

APP_COLUMNS = [("ID", "application_id", 4), ("Opportunity", "title", 26),
               ("Organizer", "organizer_name", 16), ("Date", "event_date", 10),
               ("Status", "status", 9)]


def run(db, user):
    while True:
        choice = menu(f"Artist dashboard - {user['name']}", [
            (1, "Find opportunities and apply"),
            (2, "My applications"),
            (3, "Invitations"),
            (4, "My profile and visibility stats"),
            (5, "Edit profile"),
            (6, "See other artists (showcase)"),
            (0, "Log out"),
        ])
        try:
            if choice == "1":
                browse_events(db, lambda ev: apply_flow(db, user, ev))
            elif choice == "2":
                my_applications(db, user)
            elif choice == "3":
                invitations(db, user)
            elif choice == "4":
                profile_stats(db, user)
            elif choice == "5":
                edit_profile(db, user)
            elif choice == "6":
                browse_artists(db)
            else:
                return
        except ArtReachError as err:
            print(f"\n  ! {err}")
            pause()


def apply_flow(db, user, event):
    if not ask_yes_no("\nApply to this opportunity?"):
        return
    message = ask("Short message to the organizer", required=False)
    db.apply(event["event_id"], user["user_id"], message)
    print("  Application sent. Good luck!")


def my_applications(db, user):
    banner("My applications")
    rows = db.applications_for_artist(user["user_id"])
    show_table(rows, APP_COLUMNS)
    pending = [r for r in rows if r["status"] == "pending"]
    if pending and ask_yes_no("Withdraw a pending application?"):
        app_id = ask_int("Application ID")
        db.withdraw_application(app_id, user["user_id"])
        print("  Application withdrawn.")
    pause()


def invitations(db, user):
    banner("Invitations")
    rows = db.invitations_for_artist(user["user_id"])
    show_table(rows, [("ID", "invitation_id", 4), ("Opportunity", "title", 26),
                      ("From", "organizer_name", 16),
                      ("Deadline", "deadline", 10), ("Status", "status", 9)])
    if any(r["status"] == "pending" for r in rows):
        if ask_yes_no("Respond to an invitation?"):
            inv_id = ask_int("Invitation ID")
            accept = ask_yes_no("Accept it")
            db.respond_invitation(inv_id, user["user_id"], accept)
            print("  Invitation accepted." if accept
                  else "  Invitation declined.")
    pause()


def profile_stats(db, user):
    me = db.get_user(user["user_id"])
    print_artist(me)
    stats = db.artist_stats(user["user_id"])
    print("\n Your reach")
    print(f"   Profile views        : {stats['profile_views']}")
    print(f"   Applications pending : {stats['pending']}")
    print(f"   Accepted             : {stats['accepted']}")
    print(f"   Rejected             : {stats['rejected']}")
    print(f"   Invitations waiting  : {stats['invitations']}")
    pause()


def edit_profile(db, user):
    me = db.get_user(user["user_id"])
    banner("Edit profile (Enter keeps the current value)")
    name = ask("Name", default=me["name"])
    print("Discipline (current: %s)" % (me["discipline"] or "-"))
    discipline = ask_choice("Choose", DISCIPLINES)
    city = ask("City", default=me["city"] or None, required=False)
    bio = ask("Bio", default=me["bio"] or None, required=False)
    link = ask("Portfolio link", default=me["portfolio_url"] or None,
               required=False)
    db.update_profile(user["user_id"], name=name, discipline=discipline,
                      city=city, bio=bio, portfolio_url=link)
    print("  Profile updated.")
    pause()
