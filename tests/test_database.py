import unittest
from datetime import date, timedelta

from artreach.database import ArtReachError, Database, check_password, \
    hash_password


def day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.artist = self.db.create_user("Ana", "ana@x.com", "secret1",
                                          "artist", "Kigali", "Music")
        self.artist2 = self.db.create_user("Bo", "bo@x.com", "secret1",
                                           "artist", "Huye", "Dance")
        self.org = self.db.create_user("Org", "org@x.com", "secret1",
                                       "organizer", "Kigali")
        self.event = self.make_event()

    def make_event(self, spots=1, deadline=10, date_=20, org=None):
        return self.db.create_event(org or self.org, "Show", "d", "Concert",
                                    "Music", "Kigali", day(date_),
                                    day(deadline), "pay", spots)

    def test_password_hash(self):
        stored = hash_password("abc")
        self.assertTrue(check_password("abc", stored))
        self.assertFalse(check_password("abd", stored))

    def test_duplicate_email_case_insensitive(self):
        with self.assertRaises(ArtReachError):
            self.db.create_user("X", "ANA@x.com", "secret1", "artist")

    def test_authenticate(self):
        self.assertIsNotNone(self.db.authenticate("ana@x.com", "secret1"))
        self.assertIsNone(self.db.authenticate("ana@x.com", "nope"))
        self.assertIsNone(self.db.authenticate("ghost@x.com", "secret1"))

    def test_deadline_after_event_rejected(self):
        with self.assertRaises(ArtReachError):
            self.make_event(deadline=30, date_=20)

    def test_zero_spots_rejected(self):
        with self.assertRaises(ArtReachError):
            self.make_event(spots=0)

    def test_apply_and_duplicate(self):
        self.db.apply(self.event, self.artist, "hi")
        with self.assertRaises(ArtReachError):
            self.db.apply(self.event, self.artist, "again")

    def test_apply_closed_or_expired(self):
        expired = self.make_event(deadline=-1, date_=5)
        with self.assertRaises(ArtReachError):
            self.db.apply(expired, self.artist)
        self.db.set_event_status(self.event, self.org, "closed")
        with self.assertRaises(ArtReachError):
            self.db.apply(self.event, self.artist)

    def test_expired_not_listed(self):
        self.make_event(deadline=-1, date_=5)
        self.assertEqual(len(self.db.list_events()), 1)

    def test_accept_fills_and_autocloses(self):
        a1 = self.db.apply(self.event, self.artist)
        a2 = self.db.apply(self.event, self.artist2)
        self.db.decide_application(a1, self.org, "accepted")
        self.assertEqual(self.db.get_event(self.event)["status"], "closed")
        with self.assertRaises(ArtReachError):
            self.db.decide_application(a2, self.org, "accepted")

    def test_only_owner_decides(self):
        other = self.db.create_user("O2", "o2@x.com", "secret1", "organizer")
        app = self.db.apply(self.event, self.artist)
        with self.assertRaises(ArtReachError):
            self.db.decide_application(app, other, "accepted")
        with self.assertRaises(ArtReachError):
            self.db.delete_event(self.event, other)

    def test_withdraw_only_pending(self):
        app = self.db.apply(self.event, self.artist)
        self.db.decide_application(app, self.org, "rejected")
        with self.assertRaises(ArtReachError):
            self.db.withdraw_application(app, self.artist)
        app2 = self.db.apply(self.event, self.artist2)
        self.db.withdraw_application(app2, self.artist2)
        self.assertEqual(self.db.applications_for_artist(self.artist2), [])

    def test_delete_event_cascades(self):
        self.db.apply(self.event, self.artist)
        self.db.invite(self.event, self.org, self.artist2)
        self.db.delete_event(self.event, self.org)
        count = lambda t: self.db.conn.execute(  # noqa: E731
            f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        self.assertEqual((count("applications"), count("invitations")), (0, 0))

    def test_invitation_accept_creates_application(self):
        inv = self.db.invite(self.event, self.org, self.artist, "join us")
        with self.assertRaises(ArtReachError):
            self.db.invite(self.event, self.org, self.artist)
        self.db.respond_invitation(inv, self.artist, True)
        apps = self.db.applications_for_artist(self.artist)
        self.assertEqual(apps[0]["status"], "accepted")
        with self.assertRaises(ArtReachError):
            self.db.respond_invitation(inv, self.artist, False)

    def test_invite_requires_artist_and_ownership(self):
        with self.assertRaises(ArtReachError):
            self.db.invite(self.event, self.org, self.org)
        with self.assertRaises(ArtReachError):
            self.db.invite(self.event, self.artist, self.artist2)

    def test_profile_views_and_search(self):
        self.db.view_artist(self.artist)
        self.db.view_artist(self.artist)
        self.assertEqual(self.db.get_user(self.artist)["profile_views"], 2)
        self.assertEqual(self.db.list_artists()[0]["name"], "Ana")
        self.assertEqual(len(self.db.list_artists(discipline="Dance")), 1)
        with self.assertRaises(ArtReachError):
            self.db.view_artist(self.org)

    def test_event_filters(self):
        self.assertEqual(len(self.db.list_events(city="kig")), 1)
        self.assertEqual(len(self.db.list_events(discipline="Dance")), 0)
        self.assertEqual(len(self.db.list_events(keyword="Sho")), 1)

    def test_stats(self):
        self.db.apply(self.event, self.artist)
        self.assertEqual(self.db.artist_stats(self.artist)["pending"], 1)
        self.assertEqual(self.db.organizer_stats(self.org)["pending"], 1)

    def test_update_profile(self):
        self.db.update_profile(self.artist, bio="new", role="organizer")
        user = self.db.get_user(self.artist)
        self.assertEqual((user["bio"], user["role"]), ("new", "artist"))


if __name__ == "__main__":
    unittest.main()
