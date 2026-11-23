"""Menu for logged-in organizers."""
from .database import ArtReachError, DISCIPLINES, EVENT_TYPES
from .utils import (ask, ask_choice, ask_date, ask_int, ask_yes_no, banner,
                    menu, pause, show_table)
from .views import EVENT_COLUMNS, browse_artists, print_event


def run(db, user):
    while True:
        choice = menu(f"Organizer dashboard - {user['name']}", [
            (1, "Post an opportunity"),
            (2, "My opportunities"),
            (3, "Review applicants"),
            (4, "Open / close an opportunity"),
            (5, "Delete an opportunity"),
            (6, "Find artists and send an invitation"),
            (7, "Summary"),
            (0, "Log out"),
        ])
        try:
            if choice == "1":
                post_event(db, user)
            elif choice == "2":
                list_mine(db, user)
            elif choice == "3":
                review(db, user)
            elif choice == "4":
                toggle(db, user)
            elif choice == "5":
                delete(db, user)
            elif choice == "6":
                find_and_invite(db, user)
            elif choice == "7":
                summary(db, user)
            else:
                return
        except ArtReachError as err:
            print(f"\n  ! {err}")
            pause()


def post_event(db, user):
    banner("Post an opportunity")
    title = ask("Title")
    description = ask("Description", required=False)
    print("Type:")
    etype = ask_choice("Choose", EVENT_TYPES)
    print("Discipline wanted:")
    discipline = ask_choice("Choose", DISCIPLINES)
    city = ask("City", default=user["city"] or None)
    event_date = ask_date("Event date")
    deadline = ask_date("Application deadline")
    pay = ask("Pay / perks (e.g. 50,000 RWF, free stall)", required=False)
    spots = ask_int("Number of artists needed", 1, 1000)
    event_id = db.create_event(user["user_id"], title, description, etype,
                               discipline, city, event_date, deadline, pay,
                               spots)
    print(f"  Published as opportunity #{event_id}.")
    pause()


def list_mine(db, user):
    banner("My opportunities")
    rows = db.events_by_organizer(user["user_id"])
    show_table(rows, EVENT_COLUMNS + [("Status", "status", 6)])
    pause()


def review(db, user):
    banner("Review applicants")
    rows = db.events_by_organizer(user["user_id"])
    show_table(rows, EVENT_COLUMNS)
    if not rows:
        pause()
        return
    event_id = ask_int("Event ID")
    apps = db.applications_for_event(event_id, user["user_id"])
    show_table(apps, [("ID", "application_id", 4), ("Artist", "artist_name", 20),
                      ("Field", "discipline", 14), ("Status", "status", 9),
                      ("Message", "message", 28)])
    if not apps:
        pause()
        return
    app_id = ask_int("Application ID to decide (0 to go back)", 0)
    if app_id == 0:
        return
    accept = ask_yes_no("Accept this artist (n = reject)")
    db.decide_application(app_id, user["user_id"],
                          "accepted" if accept else "rejected")
    print("  Decision saved.")
    pause()


def toggle(db, user):
    banner("Open / close an opportunity")
    show_table(db.events_by_organizer(user["user_id"]),
               EVENT_COLUMNS + [("Status", "status", 6)])
    event_id = ask_int("Event ID")
    event = db.get_event(event_id)
    if event is None or event["organizer_id"] != user["user_id"]:
        raise ArtReachError("You have no event with that ID.")
    new = "closed" if event["status"] == "open" else "open"
    db.set_event_status(event_id, user["user_id"], new)
    print(f"  Opportunity is now {new}.")
    pause()


def delete(db, user):
    banner("Delete an opportunity")
    show_table(db.events_by_organizer(user["user_id"]), EVENT_COLUMNS)
    event_id = ask_int("Event ID")
    if ask_yes_no("This also removes its applications. Delete"):
        db.delete_event(event_id, user["user_id"])
        print("  Deleted.")
    pause()


def find_and_invite(db, user):
    def invite_flow(artist):
        events = [e for e in db.events_by_organizer(user["user_id"])
                  if e["status"] == "open"]
        if not events:
            print("\n You have no open opportunities to invite for.")
            return
        if not ask_yes_no("\nInvite this artist to one of your opportunities?"):
            return
        show_table(events, EVENT_COLUMNS)
        event_id = ask_int("Event ID")
        message = ask("Personal message", required=False)
        db.invite(event_id, user["user_id"], artist["user_id"], message)
        print("  Invitation sent.")

    browse_artists(db, invite_flow)


def summary(db, user):
    s = db.organizer_stats(user["user_id"])
    banner("Summary")
    print(f"  Opportunities posted : {s['events']} ({s['open_events']} open)")
    print(f"  Applications received: {s['applications']}")
    print(f"  Waiting for review   : {s['pending']}")
    pause()
