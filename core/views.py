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
from datetime import datetime

from config import *
from models import users, bought_products, products, engine
from db_base import UserDatabaseHandler
from helper_functions import generate_password_hash, check_password_hash



logging.basicConfig(filename = ROOT_PATH + "/main_logger.log", level = logging.DEBUG )

"""
status codes FAQ:
    200 -- OK
    400 -- Bad Request
    500 -- Internal Error
    201 -- Created
    304 -- Not Modified
    404 -- Not Found
    401 -- Unauthorized
    403 -- Forbidden
"""


class Application(tornado.web.Application):

    """
    Application class 
    """

    def __init__(self):

        handlers = [
            (r"/users", UsersHandler),
            (r"/user", UserHandler)
        ]
        settings = {
            "debug": DEBUG
        }
        super(Application, self).__init__(handlers, **settings)
        self.conn = engine.connect()


class BaseHandler(tornado.web.RequestHandler):

    def __init__(self):
        self.conn = engine.connect()

    def prepare(self):
        # Put XMLHttpRequest check here
        pass


    def generic_resp(status, message, _meta = None):

        self.set_status(status)
        self.write(json.loads(dict(status = status, message = message, _meta = _meta)))

class UsersHandler(BaseHandler, UserDatabaseHandler):

    def get(self):

        """
        Return json file containing list of users,
        and additional metadata

        example url: www.base_adress.com/users?limit=10&offset=20

        Response Codes:
            200 -- OK
            500 -- Server Error

        """
        limit = self.get_query_argument("limit", 10)
        offset = self.get__query_argument("offset", 0)
        try:
            list_of_users = self.list_all_users(limit, offset)
            number_of_users = self.get_number_of_users()

            result = dict()
            result["users"] = list_of_users
            result["_metadata"] = dict()
            result["_metadata"]["total"] = number_of_users
            result["_metadata"]["limit"] = limit
            result["_metadata"]["offset"] = offset
            result["status"] = 200
            result["message"] = "OK"

            return json.loads(result)
            self.finish()
        except:
            self.generic_resp(500, "Server Error")
            self.finish()

    def post(self):
        """
        Create new user,
        body should contain valid json file with fields:
            username
            password
            email
            TODO ip_adress (optional)

        example url : www.base.com/users

        Response Codes:
            201 -- Account Created
            304 -- Not Modified ( Wrong credentials )
            500 -- Server Error
        """

        data = json.dumps(self.request.body)
        # Process data  -- remove whitespace
        # Validate data here
        if not self.credentials_unique(data["username"], data["email"]):
            self.generic_resp(304, "Not Modified", _meta = "Username or email not unique" )
        data["password"] = generate_password(data["password"])
        data["joined"] = datetime.now()

        try:
            id = self.create_user(data)
            if id:
                self.generic_resp(201, "Success")
                self.finish()
        except Exception as e:
            self.generic_resp(500, "Server Error")
            self.finish()


class UserHandler(BaseHandler, UserDatabaseHandler):

    def get(self):
        """
        Return user Information 

        example url: www.base.com/user?uuid=21323e1s-123123c-123123
        """
        pass


    def put(self):
        """
        Update user_information 
        //needs to be validated
        """
        pass
    def delete(self):
        """
        Delete user 
        //needs to be validated
        """
        pass


if __name__ == "__main__":

    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    tornado.options.parse_command_line()
    app = Application()
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    
