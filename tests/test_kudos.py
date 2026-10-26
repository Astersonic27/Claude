import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

from werkzeug.security import generate_password_hash

from app import create_app


class KudosTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        self.app = create_app({"TESTING": True, "DATABASE": self.path, "RATE_LIMIT_PER_HOUR": 3})
        with closing(sqlite3.connect(self.path)) as c:
            for u, n, a in [("admin", "Admin", 1), ("ann", "Ann", 0), ("bob", "Bob", 0), ("cy", "Cy", 0)]:
                c.execute("INSERT INTO users (username, display_name, password_hash, is_admin) VALUES (?,?,?,?)",
                          (u, n, generate_password_hash("pw"), a))
            c.commit()
            self.ids = {name: uid for uid, name in c.execute("SELECT id, username FROM users")}

    def tearDown(self):
        os.remove(self.path)

    def login(self, username):
        c = self.app.test_client()
        r = c.post("/login", data={"username": username, "password": "pw"})
        self.assertEqual(r.status_code, 302)
        with c.session_transaction() as s:
            c.csrf = s["csrf"]
        return c

    def post(self, c, url, json=None, method="post"):
        return getattr(c, method)(url, json=json, headers={"X-CSRF-Token": c.csrf})

    def give(self, c, to, msg="Great work!"):
        return self.post(c, "/api/kudos", {"recipient_id": self.ids[to], "message": msg})


class TestAuth(KudosTestCase):
    def test_login_failure(self):
        r = self.app.test_client().post("/login", data={"username": "ann", "password": "nope"})
        self.assertEqual(r.status_code, 401)

    def test_api_requires_login(self):
        c = self.app.test_client()
        self.assertEqual(c.get("/api/kudos").status_code, 401)
        self.assertEqual(c.get("/api/users").status_code, 401)

    def test_dashboard_redirects_when_anonymous(self):
        self.assertEqual(self.app.test_client().get("/").status_code, 302)

    def test_csrf_required(self):
        c = self.login("ann")
        r = c.post("/api/kudos", json={"recipient_id": self.ids["bob"], "message": "hi"})
        self.assertEqual(r.status_code, 403)

    def test_security_headers(self):
        r = self.login("ann").get("/")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])


class TestGiveKudos(KudosTestCase):
    def test_user_list_excludes_self(self):
        names = [u["name"] for u in self.login("ann").get("/api/users").get_json()["users"]]
        self.assertNotIn("Ann", names)
        self.assertIn("Bob", names)

    def test_create_and_see_in_feed(self):
        c = self.login("ann")
        r = self.give(c, "bob", "  Thanks for the help  ")
        self.assertEqual(r.status_code, 201)
        feed = self.login("cy").get("/api/kudos").get_json()["kudos"]
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0]["message"], "Thanks for the help")
        self.assertEqual(feed[0]["sender"]["name"], "Ann")

    def test_validation(self):
        c = self.login("ann")
        self.assertEqual(self.give(c, "bob", "   ").status_code, 422)
        self.assertEqual(self.give(c, "bob", "x" * 501).status_code, 422)
        self.assertEqual(self.give(c, "ann").status_code, 422)  # self kudos
        self.assertEqual(self.post(c, "/api/kudos", {"recipient_id": 9999, "message": "hi"}).status_code, 422)
        self.assertEqual(self.post(c, "/api/kudos", {"recipient_id": "2", "message": "hi"}).status_code, 422)
        self.assertEqual(self.post(c, "/api/kudos", {"recipient_id": True, "message": "hi"}).status_code, 422)
        self.assertEqual(self.give(c, "bob", "x" * 500).status_code, 201)

    def test_bad_json(self):
        c = self.login("ann")
        r = c.post("/api/kudos", data="not json", headers={"X-CSRF-Token": c.csrf})
        self.assertEqual(r.status_code, 400)

    def test_duplicate_blocked(self):
        c = self.login("ann")
        self.assertEqual(self.give(c, "bob", "Nice one").status_code, 201)
        self.assertEqual(self.give(c, "bob", "nice ONE").status_code, 409)
        self.assertEqual(self.give(c, "cy", "Nice one").status_code, 201)  # different recipient is fine

    def test_rate_limit(self):
        c = self.login("ann")
        for i in range(3):
            self.assertEqual(self.give(c, "bob", f"msg {i}").status_code, 201)
        self.assertEqual(self.give(c, "bob", "one too many").status_code, 429)

    def test_script_stored_as_text(self):
        c = self.login("ann")
        self.give(c, "bob", "<script>alert(1)</script>")
        # API returns raw text as JSON; the UI renders it via textContent (never innerHTML).
        self.assertEqual(c.get("/api/kudos").get_json()["kudos"][0]["message"], "<script>alert(1)</script>")
        self.assertNotIn("innerHTML", open(os.path.join(os.path.dirname(__file__), "..", "app", "static", "app.js")).read())

    def test_feed_pagination(self):
        self.app.config["RATE_LIMIT_PER_HOUR"] = 100
        c = self.login("ann")
        for i in range(5):
            self.give(c, "bob", f"m{i}")
        p1 = c.get("/api/kudos?limit=2").get_json()
        self.assertEqual([k["message"] for k in p1["kudos"]], ["m4", "m3"])
        p2 = c.get(f"/api/kudos?limit=2&before_id={p1['next_before_id']}").get_json()
        self.assertEqual([k["message"] for k in p2["kudos"]], ["m2", "m1"])
        p3 = c.get(f"/api/kudos?limit=2&before_id={p2['next_before_id']}").get_json()
        self.assertEqual([k["message"] for k in p3["kudos"]], ["m0"])
        self.assertIsNone(p3["next_before_id"])
        self.assertEqual(c.get("/api/kudos?limit=abc").status_code, 400)


class TestModeration(KudosTestCase):
    def setUp(self):
        super().setUp()
        self.ann, self.admin = self.login("ann"), self.login("admin")
        self.kid = self.give(self.ann, "bob", "something rude").get_json()["kudos"]["id"]

    def feed_ids(self):
        return [k["id"] for k in self.login("cy").get("/api/kudos").get_json()["kudos"]]

    def test_non_admin_forbidden(self):
        self.assertEqual(self.post(self.ann, f"/api/admin/kudos/{self.kid}/hide", {}).status_code, 403)
        self.assertEqual(self.post(self.ann, f"/api/admin/kudos/{self.kid}", {}, method="delete").status_code, 403)
        self.assertEqual(self.ann.get("/api/admin/kudos").status_code, 403)

    def test_hide_removes_from_public_feed_and_unhide_restores(self):
        r = self.post(self.admin, f"/api/admin/kudos/{self.kid}/hide", {"reason": "inappropriate"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(self.kid, self.feed_ids())
        row = self.admin.get("/api/admin/kudos?status=hidden").get_json()["kudos"][0]
        self.assertFalse(row["is_visible"])
        self.assertEqual(row["moderation_reason"], "inappropriate")
        self.assertIsNotNone(row["moderated_at"])
        self.post(self.admin, f"/api/admin/kudos/{self.kid}/unhide", {})
        self.assertIn(self.kid, self.feed_ids())

    def test_delete_is_permanent_and_audited(self):
        self.assertEqual(self.post(self.admin, f"/api/admin/kudos/{self.kid}", {"reason": "spam"}, method="delete").status_code, 200)
        self.assertNotIn(self.kid, self.feed_ids())
        with closing(sqlite3.connect(self.path)) as c:
            log = c.execute("SELECT action, reason, message FROM moderation_log").fetchall()
        self.assertEqual(log, [("delete", "spam", "something rude")])

    def test_missing_kudos_404(self):
        self.assertEqual(self.post(self.admin, "/api/admin/kudos/9999/hide", {}).status_code, 404)

    def test_default_visible_in_schema(self):
        with closing(sqlite3.connect(self.path)) as c:
            c.execute("INSERT INTO kudos (sender_id, recipient_id, message) VALUES (2,3,'x')")
            self.assertEqual(c.execute("SELECT is_visible FROM kudos ORDER BY id DESC LIMIT 1").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
