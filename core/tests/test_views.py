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
        return Application(self.conn)


    def test_saving_user_method(self):


        data = dict()
        data["user"] = dict(
            username = u"kornad2",
            password = "deprofundis",
            email = "depro@dessspro.com"
        )

        resp = self.fetch("/users", method = "POST", body = json.dumps(data))

        # self.assertEquals(201, resp.code)
        print(resp.code)
        print(resp.body)

        resp = self.fetch("/users")
        print resp.body




if __name__ == "__main__":
    tornado.testing.main()


