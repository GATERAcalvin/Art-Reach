"""Screens shared by guests, artists and organizers."""
from .database import ArtReachError, DISCIPLINES, EVENT_TYPES
from .utils import (ask, ask_choice, ask_int, banner, clip, pause,
                    show_table)

EVENT_COLUMNS = [
    ("ID", "event_id", 4), ("Title", "title", 28), ("Type", "event_type", 14),
    ("Field", "discipline", 12), ("City", "city", 10),
    ("Deadline", "deadline", 10), ("Spots", "spots_left", 5),
]


def print_event(event):
    banner(event["title"])
    print(f" Organizer   : {event['organizer_name']}")
    print(f" Type / field: {event['event_type']} / {event['discipline']}")
    print(f" Where / when: {event['city']}, {event['event_date']}")
    print(f" Apply by    : {event['deadline']}")
    print(f" Pay / perks : {event['compensation'] or 'Not stated'}")
    print(f" Spots left  : {event['spots_left']} of {event['spots']}"
          f"  [{event['status']}]")
    print(f"\n {event['description'] or ''}")


def print_artist(artist):
    banner(artist["name"])
    print(f" Discipline : {artist['discipline'] or '-'}")
    print(f" City       : {artist['city'] or '-'}")
    print(f" Portfolio  : {artist['portfolio_url'] or '-'}")
    print(f" Profile views: {artist['profile_views']}")
    print(f"\n {artist['bio'] or ''}")


def browse_events(db, on_select=None):
    """Search/filter open opportunities. on_select(event) enables applying."""
    while True:
        banner("Browse opportunities")
        print("Filter by (leave blank/skip for any):")
        discipline = ask_choice("Discipline", DISCIPLINES, allow_skip=True)
        etype = ask_choice("Type", EVENT_TYPES, allow_skip=True)
        city = ask("City", required=False)
        keyword = ask("Keyword", required=False)
        events = db.list_events(discipline, city or None, etype, keyword or None)
        print(f"\n{len(events)} open opportunities found.")
        show_table(events, EVENT_COLUMNS)
        if not events:
            pause()
            return
        event_id = ask_int("Enter an event ID to view details (0 to go back)",
                           0)
        if event_id == 0:
            return
        event = db.get_event(event_id)
        if event is None:
            print("  No event with that ID.")
            pause()
            continue
        print_event(event)
        if on_select:
            on_select(event)
        else:
            print("\n Log in as an artist to apply.")
        pause()
        return


def browse_artists(db, on_select=None):
    """Public showcase; opening a profile counts as a view."""
    banner("Artist showcase")
    discipline = ask_choice("Discipline", DISCIPLINES, allow_skip=True)
    city = ask("City", required=False)
    keyword = ask("Keyword", required=False)
    artists = db.list_artists(discipline, city or None, keyword or None)
    show_table(artists, [("ID", "user_id", 4), ("Name", "name", 22),
                         ("Field", "discipline", 18), ("City", "city", 10),
                         ("Views", "profile_views", 5)])
    if not artists:
        pause()
        return
    artist_id = ask_int("Enter an artist ID to open the profile (0 to go back)",
                        0)
    if artist_id == 0:
        return
    try:
        artist = db.view_artist(artist_id)
    except ArtReachError as err:
        print(f"  {err}")
        pause()
        return
    print_artist(artist)
    if on_select:
        on_select(artist)
    pause()


def short(text, width=40):
    return clip(text, width)
