'''
File: views.py
Author: Konrad Wasowicz
Description: Base views classes
'''
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
    accepts (mandatory) sqlalchemy connection object in constructor
    """

    def __init__(self, conn):
        handlers = [
            (r"/users", UsersHandler),
            (r"/user", UserHandler)
        ]
        settings = {
            "debug": DEBUG
        }
        super(Application, self).__init__(handlers, **settings)
        self.conn = conn


class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.conn = self.application.conn

    def initialize(self):
        pass

    def prepare(self):
        self.set_header("Content-Type", "application/json")
        # Put XMLHttpRequest check here


    def generic_resp(self, status, message, _meta = None):

        self.write(json.dumps(dict(status = status, message = message, _meta = _meta)))
        self.set_status(status)
        self.finish()

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
        offset = self.get_query_argument("offset", 0)
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

            self.write(json.dumps(result))
            self.finish()
        except Exception as e:
            self.generic_resp(500, "Server Error", str(e))
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
            400 -- Bad Request( Wrong credentials )
            500 -- Server Error
        """

        if not self.request.body:
            self.generic_resp(404, "Not Found")
        rec = json.loads(self.request.body)
        # Process data  -- remove whitespace
        # Validate data here
        data = rec["user"]
        check = True
        for field in ("username", "email", "password"):
            if field not in data.keys():
                self.generic_resp(400, "Bad Request", "Missing fields")
                return
        else:
            try:
                if not self.credentials_unique(data["username"], data["email"]):
                    self.generic_resp(400, "Bad Request", "Username and password have to be unique")
                    return
                data["password"] = generate_password_hash(data["password"])
                # TODO think abot parsing date
                data["joined"] = datetime.now().date()
                try:
                    id = self.create_user(data)
                    self.generic_resp(201, "Created")
                    return
                except Exception as e:
                    self.generic_resp(500, "Server Error", str(e))
                    return
            except Exception as e:
                self.generic_resp(500, "Server Error", str(e))
                return


class UserHandler(BaseHandler, UserDatabaseHandler):

    def __init__(self):
        self.conn = self.application.conn

    def get(self):
        """
        Return single user Information 

        Codes:
            404 -- if user not found or uuid doesnt exist
            200 -- OK
            500 -- Server Error

        example address: www.base.com/user?uuid=xxxx-xxxx-xxxx

        """
                
        user_uuid = self.get_query_argument("uuid")
        if not user_uuid:
            self.generic_resp(404, "Not Found", "Missing uuid")
            return
        else:
            try:
                user_data = self.get_user(user_uuid)
                if not user_data:
                    self.generic_resp(404, "Not Found", "User doesnt exist")
                else:
                    result = dict()
                    result["user"] = user_data
                    result["status"] = 200
                    result["message"] = "OK"
                    self.write(json.dumps(result))
                    self.finish()
            except:
                self.generic_resp(500, "Server Error")

    def put(self):
        """
        Update user_information 
        //needs to be authenticated
        """
        user_uuid = self.get_query_argument("uuid")
        if not user_uuid:
            self.generic_resp(404, "Not Found")
            return
        else:
            data = self.request.body
            update_data = json.dumps(data)["update"]

            # refactor it
            # for update_fields in update_data:
            #     if update_field not in CUSTOM_USER_FIELDS:
            #         self.generic_resp(400, "Bad Request", "Missing update fields")

            try:
                user_id = self.update_user(update_data)
                if not user_id:
                    self.generic_resp(500, "Server Error")
                else:
                    self.generic_resp(201, "Created", "Data succesfully updated")

            except Exception as e:
                self.generic_resp(500, "Server Error", str(e))


    def delete(self):
        """
        Delete user 
        //needs to be validated
        """
        user_uuid = self.get_query_argument("uuid")
        if not user_uuid:
            self.generic_resp(404, "Not Found")

        else:
            # Authenticate here
            try:
                self.delete_user(user_uuid)
            except Exception as e:
                self.generic_resp(500, "Server Error", str(e))



if __name__ == "__main__":

    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    tornado.options.parse_command_line()
    app = Application(engine.connect())
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    
