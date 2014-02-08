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
from db_base import UserDatabaseHandler, ProductDatabaseHandler
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
            list_of_users = self.list_all_users(limit, offset, safe = True)
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
            return
        except Exception as e:
            self.generic_resp(500, "Server Error", str(e))
            self.finish()
            return

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
            500 -- Server Error - see _meta key for info
        """

        if not self.request.body:
            self.generic_resp(404, "Not Found")
        rec = json.loads(self.request.body)
        # Process data  -- remove whitespace
        # Validate data here
        # Should be validated on frontend side first
        data = rec["user"]
        check = True
        for field in ("username", "email", "password"):
            if field not in data.keys():
                self.generic_resp(400, "Bad Request", "Missing fields")
                # return
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


    def authenticate_user(self, unique, password):
        """
        Basic authentication function 
        requires unique identifier (username or uuid) and password
        Returns : bool
        """
        user = self.get_credentials(unique)

        if not user:
            return False

        authenticated = check_password_hash(password, user[1])
        return authenticated



    def get(self):
        """
        Return single user Information 

        Codes:
            404 -- if user not found or uuid doesnt exist
            200 -- OK
            500 -- Server Error -- see _meta key for info

        example addresses: www.base.com/user?id=xxxx-xxxx-xxxx&password=y&direct=0
                           www.base.com/user?id=konrad&direct=1
                           www.base.com/user?id=xxxx-xxxx-xxxx

        query parameters:
            id -- unique user identifier : uuid or username
            password -- (optional) if provided authenticates
            the user and gives detailed account info
            direct -- whether it is direct connection (username provided - 1)
            or remote (uuid is checked - 0) defaults to 0

        """
                
        identifier = self.get_query_argument("id")
        password = self.get_query_argument("password", None)
        direct_arg = self.get_query_argument("direct", 0)
        try:
            direct = bool(int(direct_arg))
        except:
            direct = 0

        visitor = True
        if not identifier:
            self.generic_resp(404, "Not Found", "Missing uuid")
            return
        if password:
            auth = self.authenticate_user(identifier, password)
            if auth:
                visitor = False
        try:
            # if authenticated
            user_data = self.get_user(identifier, safe = visitor, direct = direct)
            if not user_data:
                self.generic_resp(404, "Not Found", "User doesnt exist")
                return
            else:
                result = dict()
                result["user"] = user_data
                result["status"] = 200
                result["message"] = "OK"
                self.set_status(200)
                self.write(json.dumps(result))
                self.finish()
                return
        except Exception as e:
            self.generic_resp(500, "Server Error", str(e))
            return

    def put(self):
        """
        Update user_information 
        //needs to be authenticated
        sample requests:
            www.base.com/user?username=x&password=y


        body:
            json file containing data that can be modified
            update: data containing values to be updated eg.
            'update':{
                'password': 'zmieniony',
                'email': 'zmieniony@gmail.com'
            }
            All fields that dont exist in CUSTOM_USER_FIELDS in config.py
            are discarded

            If updated correctly returns all updated fields info in _meta key
            
            Status codes:
                403 -- if no username or password or failed authentication
                304 -- if no data provided
                201 -- if updated succesfuly
                500 -- internal server error, see _meta key for info

        """
        username = self.get_query_argument("username")
        password = self.get_query_argument("password")

        if not username or not password:
            self.generic_resp(403, "Forbidden")
            return
        authenticated = self.authenticate_user(username, password)
        if not authenticated:
            self.generic_resp(403, "Forbidden")
            return
        data = self.request.body
        if not data or not "update" in json.loads(data).keys():
            self.set_status(304)
            self.finish()
            return
        update_data = json.loads(data)["update"]
        if "password" in update_data.keys():
            update_data["password"] = generate_password_hash(update_data["password"])
        try:
            updated = self.update_user(username, update_data, uuid = False)
            if not updated:
                self.generic_resp(500, "Server Error")
                return
            else:
                self.generic_resp(201, "Created", json.dumps(updated))
                return
        except Exception as e:
            self.generic_resp(500, "Server Error", str(e))
            return


    def delete(self):
        """
        Delete user with given username or password
        Requires Validation
        Sample request:
            www.base.com?id=x&password=y
        """
        id = self.get_query_argument("id", None)
        password = self.get_query_argument("password", None)

        if not id or not password:
            self.generic_resp(403, "Forbidden")
            return
        authenticated = self.authenticate_user(id, password)
        if not authenticated:
            self.generic_resp(403, "Forbidden")
            return
        else:
            try:
                self.delete_user(id, uuid = False)
                self.generic_resp(200, "OK")
                return
            except Exception as e:
                self.generic_resp(500, "Server Error", str(e))
                return

class AuthenticationHandler(BaseHandler):
    """
    Simple authentication view for
    comparing username and password
    implements only get method and is meant to be used 
    by async http client on backend side
    it also requires api_key generated by function that calls it

    sample request: www.base.py/auth?username=x&password=y?api_key=z
    """
    # username = self.get_query_argument("username", None)
    # password = self.get_query_argument("password", None)
    # api_key = self.get_query_argument("api_key", None)
    # pass # do it later



if __name__ == "__main__":

    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    tornado.options.parse_command_line()
    app = Application(engine.connect())
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    
