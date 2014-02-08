from tornado.testing import AsyncHTTPTestCase
import tornado.testing
import os, sys
import simplejson as json


sys.path.append("..")

from views import Application

from models import users, bought_products, products, engine, metadata
from sqlalchemy import create_engine
from sqlalchemy.sql import select
import uuid


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

    def test_getting_single_user_info(self):
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

        sel = select([users.c.user_uuid]).where(users.c.username == "konrad")
        konrad_uuid = self.conn.execute(sel).scalar()

        res = self.fetch("/user?id="+konrad_uuid , method = "GET")
        self.assertEquals(200, res.code)
        self.assertIn("konrad", res.body)
        self.assertNotIn("password", res.body)
        self.assertNotIn("deprofundis", res.body)
        nonexistent = str(uuid.uuid4())
        res = self.fetch("/user?id="+nonexistent, method = "GET")
        self.assertEquals(404, res.code)
        self.assertIn("Not Found", res.body)
        # test getting information on authenticated user
        user_data = self.fetch("/user?id=konrad&password=deprofundis&direct=1", method = "GET")
        self.assertEquals(user_data.code, 200)
        self.assertIn("password", user_data.body)
        self.assertIn("konrad", user_data.body)
        # remote get
        user_data = self.fetch("/user?id=" + konrad_uuid + "&password=deprofundis&direct=0", method = "GET")
        self.assertEquals(user_data.code, 200)
        self.assertIn("password", user_data.body)
        self.assertIn("konrad", user_data.body)
        # direct with no password
        user_data = self.fetch("/user?id=konrad&direct=1", method = "GET")
        self.assertEquals(user_data.code, 200)
        self.assertIn("konrad", user_data.body)
        self.assertNotIn("password", user_data.body)
        # direct with nonexistent account
        user_data = self.fetch("/user?id=nonexistent&direct=1")
        self.assertEquals(user_data.code, 404)
        self.assertIn("User doesnt exist", user_data.body)
        # password with nonexxistent
        user_data = self.fetch("/user?id=nonexistent&password=test")
        self.assertEquals(404, user_data.code)
        # all with nonexistent
        user_data = self.fetch("/user?id=nonexistent&password=test&direct=1")
        self.assertEquals(404, user_data.code)
        user_data = self.fetch("/user?id=nonexistent&password=test&direct=0")
        self.assertEquals(404, user_data.code)

    def test_updating_user_info(self):
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
        data["update"] = dict(
            password = "depro",
            email = "zmieniony@gmail.com"
        )
        resp = self.fetch("/user?username=konrad&password=deprofundis", method = "PUT", body= json.dumps(data))
        self.assertEquals(201, resp.code)
        self.assertIn("zmieniony@gmail.com", resp.body)
        self.assertIn("password", resp.body)
        # test wrong password
        resp = self.fetch("/user?username=konrad&password=nieprawidlowy", method = "PUT", body= json.dumps(data))
        self.assertEquals(403, resp.code)
        # test wrong username
        resp = self.fetch("/user?username=nieprawidlowy&password=nieprawidlowy", method = "PUT", body= json.dumps(data))
        self.assertEquals(403, resp.code)
        # test providing additional data
        data["update"] = dict(
            email = "crap@gmail.com",
            somecrap = "crapcrapcrap"
        )
        resp = self.fetch("/user?username=konrad&password=depro", method = "PUT", body= json.dumps(data))
        self.assertEquals(201, resp.code)
        self.assertIn("crap@gmail.com", resp.body)
        # test providing no data
        data = dict()
        resp = self.fetch("/user?username=konrad&password=depro", method = "PUT", body= json.dumps(data))
        self.assertEquals(304, resp.code)

    def test_deleting_users(self):
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

        resp = self.fetch("/user?id=konrad&password=deprofundis", method = "DELETE")

        self.assertEquals(200, resp.code )

        sel = select([users])
        res = self.conn.execute(sel).fetchall()
        self.assertEquals(1, len(res))

        resp = self.fetch("/users")
        self.assertNotIn("konrad", resp.body)


        resp = self.fetch("/user?id=malgosia&password=malgosia", method = "DELETE")

        sel = select([users])
        res = self.conn.execute(sel).fetchall()
        self.assertEquals(0, len(res))

        resp = self.fetch("/users")
        self.assertNotIn("malgosia", resp.body)

        # test for invalid credentials
        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        # username

        resp = self.fetch("/user?id=invalid&password=malgosia", method = "DELETE")
        self.assertEquals(403, resp.code )

        # password

        resp = self.fetch("/user?id=malgosia&password=invalid", method = "DELETE")
        self.assertEquals(403, resp.code )

        # not enought data

        resp = self.fetch("/user?id=malgosia", method = "DELETE")
        self.assertEquals(403, resp.code )

class TestProductOperations(AsyncHTTPTestCase):

    def get_app(self):
        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        self.conn = engine.connect()
        metadata.create_all()
        return Application(self.conn)

    def tearDown(self):
        metadata.drop_all()

        
        

if __name__ == "__main__":
    tornado.testing.main()


