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
from db_base import UserDatabaseHandler, ProductDatabaseHandler, AuthDBHandler, MiscDBHandler, BoughtDBHandler
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
            (r"/", IndexHandler),
            (r"/users", UsersHandler),
            (r"/user", UserHandler),
            (r"/user/(\w{4,20})/bought", BoughtProductsHandler),
            (r"/user/(\w{4,20})/sold", SoldProductsHandler),
            (r"/products", ProductsHandler),
            (r"/product", ProductHandler),
            (r"/products/buy", BuyProductsHandler),
            (r"/products/top", TopProductsHandler),
            (r"/auth", AuthenticationHandler),
        ]
        settings = {
            "debug": DEBUG,
            "template_path": BASE_PATH + "/templates",
            "static_path": BASE_PATH + "/static"
        }
        super(Application, self).__init__(handlers, **settings)
        self.conn = conn


class BaseHandler(tornado.web.RequestHandler):

    """
    Base handler implementing basic methods and configuring 
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

        self.required_product_fields = ("product_name", "product_desc", "price")

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
        message = "Unknown_Message"
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

    @gen.coroutine
    def remote_auth(self, username, password, persist = 0):

        """
        Simple handler for user authentication 
        persist -- (int) 1 or 0

        Returns 1 if auth ok or 0 if not
        if persist is 1 returns secure cookie
        """


        query = "/auth?username=" + username + "&password=" + password\
                + "&persist=" + str(persist)

        req = HTTPRequest(self.get_self_url(query), method = "GET")
        res = yield gen.Task(AsyncHTTPClient().fetch, req)
        raise gen.Return(res.body)

    @gen.coroutine
    def get_item_data(self, identifier, direct = 0):
        """
        Returns item information
        if direct == 1 looks by product_uuid
        """

        query = "/product?id=" + identifier + "&direct=" + str(direct)
        req = HTTPRequest(self.get_self_url(query), method = "GET")
        res = yield gen.Task(AsyncHTTPClient().fetch, req)
        raise gen.Return(res.body)
    
    @gen.coroutine
    def get_user_data(self, identifier, direct = 0):
        """
        Return user information
        if direct == 1 looks by user_uuid
        """
        query = "/user/?id=" + identifier + "&direct=" + str(direct)
        req = HTTPRequest(self.get_self_url(query), method = "GET")
        res = yield gen.Task(AsyncHTTPClient().fetch, req)
        raise gen.Return(res.body)

    @tornado.web.asynchronous
    def authenticate_user(self, unique, password):
        """
        Basic authentication function 
        used for synchronously fetch user information
        requires unique identifier (username or uuid) and password
        Returns : bool
        """
        user = self.get_credentials(unique)

        if not user:
            return False

        authenticated = check_password_hash(password, user[1])
        return authenticated


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        """
        Renders index 
        """
        self.render("index.html", host = self.request.protocol + "://" + self.request.host )

class UsersHandler(BaseHandler, UserDatabaseHandler):
    
    @tornado.web.asynchronous
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
    
    @tornado.web.asynchronous
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
                return
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



    @tornado.web.asynchronous
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
                
        identifier = self.get_query_argument("id", None)
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

    @tornado.web.asynchronous
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
            as well as _metadata with current
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
        # list_of_products["_metadata"]["category"] = category or "All"
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

                  TODO parse inserted data
        """
        authenticated = False
        sent_data = json.loads(self.request.body)
        # user_data = None
        # product_data = None
        try:
            user_data = sent_data["user"]
            product_data = sent_data["product"]
        except:
            self.generic_resp(400, "Data not parsed properly")
            return
        
        product_data.setdefault("category", "Other")

        for field in self.required_product_fields:
            if field not in product_data.keys():
                self.generic_resp(400, "Data not parsed properly")
                return

        # print "running"

        # implement cookie authentication


        resp = yield self.remote_auth(user_data["username"], user_data["password"], persist = 0)

        try:
            authenticated = int(resp)
        except Exception as e:
            self.generic_resp(500, str(e))
            return
        # print authenticated
        if authenticated == 0:
            self.generic_resp(403, "Invalid Credentials")
            return
        if not self.product_unique(product_data["product_name"]):
            self.generic_resp(400, "This product name is already taken")
            return

        # validate fields here

        parsed_product_data = product_data
        parsed_product_data["seller"] = user_data["username"]

        try:
            success = self.create_product(parsed_product_data)
            self.generic_resp(201, json.dumps(success))
            return

        except Exception as e:
            self.generic_resp(500, str(e))
            return

class ProductHandler(BaseHandler, ProductDatabaseHandler):

    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):

        """
        Get single product info 

        sample request: www.base.com/product?id=xdirect=1
        id -- unique product identifier name or uuid
        direct -- if set to 1 looks by uuid if 0 by name
        """

        identifier = self.get_query_argument("id", None)
        if not identifier:
            self.generic_resp(404)
            return

        direct = self.get_query_argument("direct", False)

        try:
            direct = bool(int(direct))
        except:
            direct = False
        try:

            res = self.get_product(identifier, direct)
            if not res:
                self.generic_resp(404)
                return

            resp = dict()
            resp["product"] = res
            resp["status"] = 200
            resp["mesasage"] = "OK"

            self.write(json.dumps(resp))
            self.set_status(200)
            return
        except Exception as e:
            self.generic_resp(500, str(e))
            self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def put(self):

        """
        Update product information
        requires body containing user data and product data

        only fields in CUSTOM_USER_FIELDS in config.py
        are permitted all the others are discarded
        returns json file containing data that has been updated

        sample update json :
            {
            "update": {
                "product_name": "wiertarka", --- required for getting uuid
                "product_desc": "jakas wiertarka",
                "price": "120zl"

            }
            "user": {
                "username": "konrad",
                "password": "test"
            }
            }
        
        Returns:
            404 -- product not found
            400 -- Wrong data input (missing fields etc)
            401 -- Authentication failed
            500 -- Server Error
            201 -- Updated
        """

        body = json.loads(self.request.body)
        if not body:
            self.generic_resp(400, "No information given")
            return

        try:
            user_data = body["user"]
            product_data = body["update"]
        except:
            self.generic_resp(400, "Data not parsed properly")
            return
    
        try:
            try:
                # authenticate user
                authenticated = yield\
                        self.remote_auth(user_data["username"], user_data["password"])
                authenticated = int(authenticated)
            except Exception as e:
                self.generic_resp(500, str(e))
                return


            if not authenticated:
                self.generic_resp(401, "Authentication failed")
                return
            
            # get full product info
            try:
                full_product_data = yield\
                        self.get_item_data(product_data["product_name"], direct = 0)
                full_product_data = json.loads(full_product_data)["product"]
                if full_product_data["seller"] != user_data["username"]:
                    self.generic_resp(401, "You dont have permission to update this item")
                    return
            except Exception as e:
                self.generic_resp(404)
                return
        except Exception as e:
            self.generic_resp(500, str(e))
            return

        try:
            result = self.update_product(full_product_data["uuid"], product_data)
            resp = dict()
            resp["status"] = 201
            resp["message"] = "Created"
            resp["updated"] = result
            self.write(json.dumps(resp))
            self.set_status(201)
            self.finish()
            return
        except Exception as e:
            self.generic_resp(500, str(e))
            return

    @gen.coroutine
    def delete(self):

        """
        Delete given product
        Sample request:
            www.base.com/product?id=wiertarka&name=konrad&password=haslo&direct=0

        query parameters:
            id -- (required) identifier of the product
            name -- (required) name of the owner
            password -- (required) user_password
            direct -- if 1 gets product by uuid else by name

            id of the owner has to match 'seller' field in products table

        """

        product_identifier = self.get_query_argument("id", None)
        username = self.get_query_argument("name", None)
        password = self.get_query_argument("password", None)
        direct = self.get_query_argument("direct", 0)
        try:
            direct = int(direct)
        except:
            direct = 0

        if not username or not password or not product_identifier:
            self.generic_resp(400, "Missing fields")
            return

        try:
            authenticated = yield self.remote_auth(username, password, persist = 0)

            try:
                authenticated = int(authenticated)
                if not authenticated:
                    self.generic_resp(401, "Authentication Failed")
                    return
            except Exception as e:
                self.generic_resp(500)
                return

            item_data = yield self.get_item_data(product_identifier, direct = direct)
            item_data = json.loads(item_data)
            if item_data["status"] != 200:
                self.generic_resp(404, "Item Not Found")
                return
            item_data = item_data["product"]

            if username != item_data["seller"]:
                self.generic_resp(401, "Permission Denied")
                return
        except Exception as e:
            self.generic_resp(500, str(e))
            return

        try:
            self.delete_product(product_identifier, uuid = direct)
            self.generic_resp(201, "Product deleted")
            return

        except Exception as e:
            self.generic_resp(500, str(e))
            return


class TopProductsHandler(BaseHandler, MiscDBHandler):
    """
    Simple handler for getting most selled products 
    accepts optional limit argument
    """
    @tornado.web.asynchronous
    def get(self):

        limit = self.get_query_argument("limit", 10)
        if limit > 40:
            limit = 40
        

        try:
            top_products = self.get_top_selling_products(limit) or "No Products"
            self.write(json.dumps(top_products))
            self.set_status(200)
            self.finish()
            return
        except Exception as e:
            self.generic_resp(500, str(e))


class BuyProductsHandler(BaseHandler, BoughtDBHandler):

    @tornado.web.asynchronous
    def post(self):
        """
        
        Basic view for buying items by users,
        implements only post method.

        Requires authentication

        Sample request: www.base.com/products/buy

        Request body should contain valid JSON file

        Sample format:
            {
                "user": 
                    "user_uuid" : "16a0182a-8f58-4c4f-93ca-4ad62287e64f" ,
                    "username" :"konrad",   --- optional
                    "password" : "test",
                    "cookie" : generated_secure_cookie here -- optional -- to implement
                },

                "product": {
                    "product_uuid": "fda4a4c4-8c8f-4fc2-8006-bab1556f3045"
                    "product_name" : "wiertarka", --optional
                    "quantity": 10
                }

            }

        """

        try:
            body = json.loads(self.request.body)
            user_data = body["user"]
            product_data = body["product"]
        except:
            self.generic_resp(400, "Data not parsed properly")
            return

    
        user_id = user_data.get("username", None)
        if not user_id:
            user_id = user_data.get("user_uuid", None)
        else:
            user_id = self.get_uuid_by_username(user_id)

        product_id = product_data.get("product_name", None)
        if not product_id:
            product_id = product_data.get("product_uuid", None)
        else:
            product_id = self.get_uuid_by_product_name(product_id)

        if not product_id or not user_id:
            self.generic_resp(404)
            return


        # authenticate
        password = user_data.get("password", None)
        quantity = product_data.get("quantity", None)
        if not password or not quantity:
            self.generic_resp(400, "Data not parsed properly")
            return
        authenticated = self.authenticate_user(user_id, password)
        if not authenticated:
            self.generic_resp(403, "Invalid username or password")
            return

        try:
            self.add_bought_product(quantity, user_id, product_id)
            self.generic_resp(201, "Bought succesfully")
        except Exception as e:
            self.generic_resp(500, str(e))


class BoughtProductsHandler(BaseHandler, BoughtDBHandler):

    """
    Implements function for getting user bought products 
    sample request
    return 404 if no items found
    www.base.com/user/konrad/bought
    """

    def get(self, username):
        try:
            resp = self.get_users_bought_products(username, uuid = False)
            if not resp:
                self.generic_resp(404)
            self.write(json.dumps(resp))
            return

        except Exception as e:
            self.generic_resp(500, str(e))

class SoldProductsHandler(BaseHandler, BoughtDBHandler):
    """
    View for gettting all items that the person is selling 
    return 404 if no items found
    """
    def get(self, username):
        try:
            resp = self.get_users_sold_products(username)
            if not resp:
                self.generic_resp(404)
            self.write(json.dumps(resp))
            return

        except Exception as e:
            self.generic_resp(500, str(e))



class AuthenticationHandler(BaseHandler, AuthDBHandler):
    """
    Simple authentication view for
    comparing username and password
    implements only get method and is meant to be used 
    by async http client on backend side
    expects following query parameters:
        username password persist -- (optional) if set to 1 returns encrypted cookie to be saved in the browser if 0 returns 1 if succesfully authenticated or 0 if not 

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
        


def main():
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    tornado.options.parse_command_line()
    app = Application(engine.connect())
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    
