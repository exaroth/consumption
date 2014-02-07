from tornado.testing import AsyncHTTPTestCase
import tornado.testing
import os, sys
import simplejson as json


sys.path.append("..")

from views import Application

from models import users, bought_products, products, engine, metadata
from sqlalchemy import create_engine


class TestUserOperations(AsyncHTTPTestCase):

    def get_app(self):
        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        self.conn = engine.connect()
        metadata.create_all()
        return Application(self.conn)

    def tearDown(self):
        metadata.drop_all()
        


    def test_saving_user_method(self):


        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )

        resp = self.fetch("/users", method = "POST", body = json.dumps(data))

        self.assertIn("201", resp.body)
        self.assertEquals(201, resp.code)

        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )


        resp = self.fetch("/users", method = "POST", body = json.dumps(data))
        self.assertIn("201", resp.body)
        self.assertIn("Created", resp.body)

        # test unique username and password

        # username

        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia2@gmail.com"
        )


        resp = self.fetch("/users", method = "POST", body = json.dumps(data))
        self.assertIn("Username and password have to be unique", resp.body)
        self.assertEquals(400, resp.code)

        # email

        data = dict()
        data["user"] = dict(
            username = u"malgosia2",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )

        resp = self.fetch("/users", method = "POST", body = json.dumps(data))
        self.assertIn("Username and password have to be unique", resp.body)
        self.assertEquals(400, resp.code)

        # test for missing fields

        data["user"] = dict(
            username = u"kuba",
            password = "kuba"

        )
        resp = self.fetch("/users", method = "POST", body = json.dumps(data))

        self.assertEquals(400, resp.code)
        self.assertIn("Missing fields", resp.body)



        data["user"] = dict(
            username = u"kuba",
            email = "kuba@gmail.com"
        )


        resp = self.fetch("/users", method = "POST", body = json.dumps(data))

        self.assertEquals(400, resp.code)
        self.assertIn("Missing fields", resp.body)

    def test_getting_user_list(self):

        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = u"kuba",
            password = "kuba",
            email = "kuba@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        resp = self.fetch("/users", method = "GET")
        self.assertIn("konrad", resp.body)
        self.assertIn("kuba", resp.body)
        self.assertIn("malgosia", resp.body)
        self.assertEquals(200, resp.code)
        self.assertIn("application/json", resp.headers.values())

        dump = json.loads(resp.body)

        self.assertEquals(3, dump["_metadata"]["total"])
        self.assertEquals(3, len(dump["users"]))



if __name__ == "__main__":
    tornado.testing.main()


