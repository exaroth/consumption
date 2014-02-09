'''
File: views.py
Author: Konrad Wasowicz
Description: Base views classes
'''
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.httpclient import AsyncHTTPClient, HTTPRequest


import tornado.options
import tornado.web
from tornado import gen
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
from db_base import UserDatabaseHandler, ProductDatabaseHandler, AuthDBHandler
from helper_functions import generate_password_hash, check_password_hash, generate_secure_cookie, check_secure_cookie



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
            (r"/user", UserHandler),
            (r"/products", ProductsHandler),
            (r"/auth", AuthenticationHandler)
        ]
        settings = {
            "debug": DEBUG
        }
        super(Application, self).__init__(handlers, **settings)
        self.conn = conn


class BaseHandler(tornado.web.RequestHandler):

    """
    Base handler implementing basic methods and configuring basic
    settings for other handlers
    """

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.conn = self.application.conn
        self.client = AsyncHTTPClient()

        self.response_codes = dict(
            Success = 200,
            Bad_Request = 400,
            Server_Error = 500,
            Created = 201,
            Not_Modified = 304,
            Not_Found = 404,
            Unauthorized = 401,
            Forbidden = 403
        )

    def initialize(self):
        pass

    def prepare(self):
        self.set_header("Content-Type", "application/json")
        # AJAX check
        # disabled for production
        if not DEBUG:
            if not "X-Requested-With" in self.request.headers or\
               self.request.headers["X-Requested-With"] != "XMLHttpRequest":
                self.set_status(404)
                self.finish()
                return


    def generic_resp(self, status_code, _meta = None):

        """
        Generic json output parser
        returns json containing status, response code,
        and additional data if provided also sets up response status
        of response
        status -- (int) compares number given to dictionary
        hof response codes if number not found sets message to unknown
        _meta -- additional data to pass to response
        sample output:
            {
                "status": 200,
                "message": "OK",
                "_meta" : "some_data"
            }
        """
        message = "Unknown"
        for key, val in self.response_codes.items():
            if val == status_code:
                message = key

        self.write(json.dumps(dict(status = status_code, message = message, _meta = _meta)))
        self.set_status(status_code)
        self.finish()

    def get_self_url(self, route):
        """
        Returns absolute path to app, given a specific route
        """

        return self.request.protocol + "://" + self.request.host + route


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
        try:
            limit = self.get_query_argument("limit", 10)
            offset = self.get_query_argument("offset", 0)
        except Exception as e:
            self.generic_resp(500, str(e))
            return
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
            self.generic_resp(500, str(e))
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
            self.generic_resp(404)
        rec = json.loads(self.request.body)
        # Process data  -- remove whitespace
        # Validate data here
        # Should be validated on frontend side first
        data = rec["user"]
        check = True
        for field in ("username", "email", "password"):
            if field not in data.keys():
                self.generic_resp(400, "Missing fields")
                # return
        try:
            if not self.credentials_unique(data["username"], data["email"]):
                self.generic_resp(400, "Username and password have to be unique")
                return
            data["password"] = generate_password_hash(data["password"])
            # TODO think abot parsing date
            data["joined"] = datetime.now().date()
            try:
                id = self.create_user(data)
                self.generic_resp(201)
                return
            except Exception as e:
                self.generic_resp(500, str(e))
                return
        except Exception as e:
            self.generic_resp(500, str(e))
            return


class UserHandler(BaseHandler, UserDatabaseHandler):

    """
    Implements methods related to operations on single user

    GET -- returns user info
    PUT -- updates user info
    DELETE -- deletes user
    """


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
            self.generic_resp(404, "Missing uuid")
            return
        if password:
            auth = self.authenticate_user(identifier, password)
            if auth:
                visitor = False
        try:
            # if authenticated
            user_data = self.get_user(identifier, safe = visitor, direct = direct)
            if not user_data:
                self.generic_resp(404, "User doesnt exist")
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
            self.generic_resp(500, str(e))
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
            self.generic_resp(403)
            return
        authenticated = self.authenticate_user(username, password)
        if not authenticated:
            self.generic_resp(403)
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
                self.generic_resp(500)
                return
            else:
                self.generic_resp(201, json.dumps(updated))
                return
        except Exception as e:
            self.generic_resp(500, str(e))
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
            self.generic_resp(403)
            return
        authenticated = self.authenticate_user(id, password)
        if not authenticated:
            self.generic_resp(403)
            return
        else:
            try:
                self.delete_user(id, uuid = False)
                self.generic_resp(200)
                return
            except Exception as e:
                self.generic_resp(500, str(e))
                return

class ProductsHandler(BaseHandler, ProductDatabaseHandler):
    """
    Similar to UsersHandler implements methods :
        GET - gets list of products
        POST -- creates new product
    """
    @tornado.web.asynchronous
    def get(self):
        """
        Get list of products 

        params: limit -- defaults to 10
                offset -- defaults to 0
                category -- (optional)limits search for product to given category

        sample request:
            www.base.com/products?limit=x&offset=y
        Returns:
            json containing list of products
            as well as _metadata containing current
            limit, offset and total number of products
        """

        limit = self.get_query_argument("limit", 10)
        offset = self.get_query_argument("offset", 0)
        category = self.get_query_argument("category", None)

        try:
            number_of_products = self.get_number_of_products()
            product_list = self.get_product_list(limit, offset, category)
        except Exception as e:
            self.generic_resp(500, str(e))
            return

        list_of_products = dict()
        list_of_products["_metadata"] = dict()
        list_of_products["_metadata"]["limit"] = limit
        list_of_products["_metadata"]["offset"] = offset
        list_of_products["_metadata"]["total"] = number_of_products
        list_of_products["_metadata"]["category"] = category or "All"
        list_of_products["products"] = product_list
        list_of_products["status"] = 200
        list_of_products["message"] = "OK"
        self.write(json.dumps(list_of_products))
        self.set_status(200)
        self.finish()


    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """
        Create new product 
        expects valid json file containing:
            'product' object with:
                product_name
                product_desc
                category (optional)
                price -- string
            'user' object with :
                username
                password 
                can be also provided from secure cookie
            'cookie' -- (optional) secure cookie sent by javascript

        Returns : 201 -- Created
                  403 -- Forbidden if authentication failed
                  500 -- Server Error
                  400 -- Bad Request
        """
        print self.response_codes
        authenticated = False
        sent_data = json.loads(self.request.body)
        user_data = sent_data["user"]

        # print "running"

        # implement cookie authentication

        path = self.get_self_url("/auth?username=" + user_data["username"]+ "&password=" + user_data["password"]+ "&persist=0")
        req = HTTPRequest(path, method = "GET")

        resp = yield self.client.fetch(req)

        try:
            authenticated = int(resp.body)
        except Exception as e:
            self.generic_resp(500, str(e))
            return

        if authenticated == 0:
            self.generic_resp(403, "Invalid Credentials")
            return
        try:
            product_data = sent_data["product"]
        except:
            self.generic_resp(400, "Data not parsed properly")
            return

        if not self.product_unique(product_data["product_name"]):
            self.generic_resp(400, "This product name is already taken")
            return

        # validate fields here

        parsed_product_data = product_data
        parsed_product_data["seller"] = user_data["username"]

        try:
            success = self.create_product(parsed_product_data)
            self.generic_resp(200, json.dumps(success))

        except Exception as e:
            self.generic_resp(500, str(e))









class AuthenticationHandler(BaseHandler, AuthDBHandler):
    """
    Simple authentication view for
    comparing username and password
    implements only get method and is meant to be used 
    by async http client on backend side
    expects following query parameters:
        username
        password
        persist -- (optional) if set to 1 returns
                    encrypted cookie to be saved in the browser
                    if 0 returns 1 if succesfully authenticated
                    or 0 if not


    sample request: www.base.py/auth?username=x&password=y?persist=1
    """
    @tornado.web.asynchronous
    def get(self):

        username = self.get_query_argument("username", None)
        password = self.get_query_argument("password", None)
        persist = self.get_query_argument("persist", False)

        if not username or not password:
            self.generic_resp(403, "username and password are required")
            return

        try:
            persist = bool(int(persist))
        except:
            persist = False

        try:
            hash = self.get_password(username, uuid = False)
        except:
            self.generic_resp(500)
            return

        authenticated = check_password_hash(password, hash)
        if not authenticated:
            self.write(str(0))
            self.finish()
            return

        if persist:
            self.write(generate_secure_cookie(username))
            self.set_status(201)
            self.finish()
            return
        self.write(str(1))
        self.finish()
        return
        


if __name__ == "__main__":

    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    tornado.options.parse_command_line()
    app = Application(engine.connect())
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    
