from tornado.testing import AsyncHTTPTestCase
import tornado.testing
import os, sys


sys.path.append("..")

from views import Application, IndexHandler


class TestUserOperations(AsyncHTTPTestCase):

    def get_app(self):
        return Application()



    def test_get_user_method(self):

        resp = self.fetch("/users")
        self.assertIn("application works", resp.body)



if __name__ == "__main__":
    tornado.testing.main()


