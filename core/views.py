from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
import tornado.options
import tornado.web
from tornado.options import define, options

define("port", default = 8000, help = "set server port", type = int)

import simplejson as json

import os, sys
import logging
import uuid
import simplejson as json

from config import *
from models import users, bought_products, products, engine
from db_base import UserDatabaseHandler
from helper_functions import generate_password, check_password



logging.basicConfig(filename = ROOT_PATH + "/main_logger.log", level = logging.DEBUG )


class Application(tornado.web.Application):

    """
    Application class 
    """

    def __init__(self):

        handlers = [
            (r"/users", UsersHandler),
        ]
        settings = {
            "debug": True
        }
        super(Application, self).__init__(handlers, **settings)
        self.conn = engine.connect()

class IndexHandler(tornado.web.RequestHandler):

    def get(self):
        self.write("application works")

class BaseHandler(tornado.web.RequestHandler):

    def __init__(self):
        self.conn = engine.connect()


    def generic_json(status, message):

        self.set_status(status)
        self.write(json.loads(dict(status = status, message = message)))

class UsersHandler(BaseHandler, UserDatabaseHandler):

    def get(self):

        """
        Return json file containing list of users,
        and additional metadata
        """
        limit = self.get_argument("limit", 10)
        offset = self.get_argument("offset", 0)

        list_of_users = self.list_all_users(limit, offset)
        number_of_users = self.get_number_of_users()

        result = dict()
        result["users"] = list_of_users
        result["_metadata"] = dict()
        result["_metadata"]["total"] = number_of_users
        result["_metadata"]["limit"] = limit
        result["_metadata"]["offset"] = offset

        return json.loads(result)

    def post(self):
        """
        Create new user
        """

        data = self.request.body
        data["password"] = generate_password(data["password"])

        try:
            id = self.create_user(data)
            if id:
                self.generic_json(201, "Success")
        except Exception as e:
            self.generic_json(500, "Server Error")




if __name__ == "__main__":

    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    tornado.options.parse_command_line()
    app = Application()
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    
