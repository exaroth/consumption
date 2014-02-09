'''
File: db_base.py
Author: Konrad Wasowicz
Description: Basic Database interaction functions
TODO -- Implement db logging hanfling
'''

import logging
from config import *
from models import users, bought_products, products, engine
from sqlalchemy.sql import select, exists
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError

logging.basicConfig(filename = ROOT_PATH + "/errors.log", level = logging.DEBUG)
import uuid

class BaseDBHandler(object):


    """
    Implements basic functions for database interaction.
    """

    def __init__(self, conn = None):
        if conn:
            self.conn = conn

    def parse_query_data(self, query, iter, id = False):
        """
        Parses tuple returned from database by sqlalchemy,  
        second argument is iterable list or tuple containing database
        field names minus primary key
        
        Keyword Arguments:
        query -- tuple with data returned from db (tuple/list),
        iter -- iterable containing field names used for parsing database
        info (list/tuple)
        id -- if set to False it will not include first item in tuple which usually is
        a an id
        """
        if type(iter) not in (tuple, list):
            raise TypeError("iter must be iterable type : list or tuple")
        if not query:
            return dict()
        if id:
            return dict(zip(iter, query))
        return dict(zip(iter, query[1:]))

    def parse_list_query_data(self, data, iter, key = "uuid", id = False):
        """
        Parses list of tuples returned from db by sqlalchemy,
        Returns dictionary containing:
            user_uuid: { user_data_returned by parse_query_data }
        
        Keyword Arguments:
        data -- tuple containing tuples :) returned from db (list/tuple),
        iter -- iterable containg field names for given table (minus pk),
        key -- field to be used as key for each entry, defaults to uuid (str)

        """
        result = dict()
        for row in data:
            temp = self.parse_query_data(row, iter, id)
            result[temp[key]] = temp
        return result

    def generate_unique_uuid(self, field_name):
        """
        Generates unique 36 characters long uuid 
        (generated by uuid.uuid4 module)
        
        Keyword Arguments:
        field_name -- column name in sqlalchemy expression language format
        to compare to, eg. users.c.user_uuid (sqlalchemy column name)
        """
        while True:
            sample_uuid = str(uuid.uuid4())
            sel = select([exists().where(field_name == sample_uuid)])
            result = self.conn.execute(sel).scalar()
            if result == 0:
                return sample_uuid
    
    def get_row(self,table, column, uuid, field_tuple):
        """
        Returns dictionary containg single row data returned from db
        
        Keyword Arguments:
        column -- sqlalchemy column name (eg. users.c.username)
        uuid -- unique uuid (str)
        field_tuple - iterable containing fields to parse dictionary against (list/tuple)
        """
        sel = select([table]).where(column == uuid)
        q = self.conn.execute(sel).fetchone()
        if not q:
            return dict()
        return self.parse_query_data(q, field_tuple)

    def get_all_rows(self, table, field_tuple, limit, offset):
        """
        Returns dictionary containing list of rows returned from table,
        see parse_list_query_data for structure of the dict
        
        Keyword Arguments:
        table -- tablename to get data from (sqlalchemy table)
        field_tuple -- iterable to parse dictionary against (list/tuple)
        limit -- limit the number of rows returned (int)
        offset -- offset for query (int)
        """
        sel = select([table]).limit(limit).offset(offset)
        res = self.conn.execute(sel).fetchall()
        return self.parse_list_query_data(res, field_tuple)

    def check_exists(self, column, value):
        """
        Checks if given value exists in table 
        
        Keyword Arguments:
        column -- sqlalchemy expression language column (eg. users.c.username)
        value -- value to search for (str)
        """
        sel = select([exists().where(column == value)])
        result = self.conn.execute(sel).scalar()
        return result

    def delete_row(self, column, value):
        """
        Deletes row that matches value 
        
        Keyword Arguments:
        column -- sqlalchemy column to search in
        value -- value to match it against
        """
        delete_q = users.delete().where(column == value)
        self.conn.execute(delete_q)



class UserDatabaseHandler(BaseDBHandler):

    """
    Base class for user database interaction
    accepts connection object as argument (optionally)
    """

    def __init__(self, *args, **kwargs):

        super(UserDatabaseHandler, self).__init__(*args, **kwargs)

        

    # not needed
    # def user_exists(self, uuid):
    #     """
    #     Checks if user with given uuid exists 
    #     """
    #     return self.check_exists(users.c.user_uuid, uuid)

    def generate_user_uuid(self):
        """
        Generate user uuid 
        """
        return self.generate_unique_uuid(users.c.user_uuid)

    def credentials_unique(self, username, email):
        """
        Checks if given credentials are already taken
        
        Keyword Arguments:
        username, email -- (str)
        Returns : bool
        """
        if not username or not email:
            raise TypeError("no username or email given")
        sel = select([exists().where(
                or_(
                    users.c.username == username,
                    users.c.email == email
                )
        )])
        try:
            result = self.conn.execute(sel).scalar()
            return not result
        except:
            raise

    def get_credentials(self, identifier):
        """
        Return username and password
        used for user verification
        identifier might be either uuid or username
        """

        sel = select([users.c.username, users.c.password])\
                .where(or_(
                    users.c.username == identifier,
                    users.c.user_uuid == identifier
                ))

        try:
            res = self.conn.execute(sel).fetchone()
            return res
        except:
            raise


    def save_user(self, data):
       """
       Create new user with given data

       Returns : primary key of the user that has been created
       
       Keyword Arguments:
       data -- dictionary containing user field names,
       must have all the keys in USER_FIELDS,
       all additional keys all discarded
       """
       els_to_insert = dict()
       for key, value in data.items():
           if key in USER_FIELDS:
               els_to_insert[key] = value
       for field in USER_FIELDS:
           if field not in els_to_insert.keys():
               raise Exception("Data not parsed properly, missing {0}".format(field))
       els_to_insert["user_uuid"] = els_to_insert["uuid"] # i screwed up :(
       del els_to_insert["uuid"]
       ins = users.insert().values(**els_to_insert)
       trans = self.conn.begin()
       try:
           res = self.conn.execute(ins)
           trans.commit()
           return res.inserted_primary_key[0]
       except:
           trans.rollback()
           logging.error("Error creating user")
           raise

    def create_user(self, data):
        """
        Wrapper for creating new user
        -Generates unique uuid
        -Checks if name and email are unique
        -Saves user to database
        see save_user, credentials_unique, generate_user_uuid for details
        
        Returns: inserted user pk or raises IntegrityError if name or email is taken
        
        Keyword Arguments:
        data -- dictionary containing values to be inserted,
        should be parsed and validated (dict)
        """

        # put unique check in view model

        # if not self.credentials_unique(data["username"], data["email"]):
        #     raise IntegrityError("Name and email must be unique")
        user_uuid = self.generate_user_uuid()
        data["uuid"] = user_uuid
        try:
            res = self.save_user(data)
            return res
        except:
            raise


    def get_user(self, identifier, safe = False, direct = False):
        """
        Get user with given uuid 
        
        Keyword Arguments:
        identifier -- unique user identifier
        safe -- if false returns full query data
        uuid -- if True looks by user_uuid field else looks by username
        direct -- if False looks by user_uuid column else by username
        """
        if not direct:
            haystack = users.c.user_uuid
        else:
            haystack = users.c.username
        try:
            if not self.check_exists(haystack, identifier):
                return dict()
            if safe:
                res = self.get_row(users, haystack, identifier, USER_FIELDS)
                for field in SECURE_USER_FIELDS:
                    del res[field]
                return res
            return self.get_row(users, haystack, identifier, USER_FIELDS)
        except:
            raise

    def delete_user(self, identifier, uuid = True):
        """
        Deletes user with given uuid 
        
        Keyword Arguments:
        uuid -- unique users uuid
        """
        if uuid:
            haystack = users.c.user_uuid
        else:
            haystack = users.c.username
        trans = self.conn.begin()
        try:
            self.delete_row(haystack, identifier)
            trans.commit()
        except:
            trans.rollback()
            logging.error("Error deleting user")
            raise

    def update_user(self, identifier, data, uuid = True):
        """
        Updates user values with given data
        
        Keyword Arguments:
        identifier -- unique user\'s uuid (if uuid = True) or username,
        data -- dictionary containg {field_name : value} (dict)
        """
        if uuid:
            haystack = users.c.user_uuid
        else:
            haystack = users.c.username
        items_to_update = dict()
        for key, value in data.items():
            if key in CUSTOM_USER_FIELDS:
                items_to_update[key] = value
        update_q = users.update()\
                .where(haystack == identifier)\
                .values(**items_to_update)
        trans = self.conn.begin()
        try:
            resp = self.conn.execute(update_q)
            trans.commit()
            return resp.last_updated_params()
        except:
            trans.rollback()
            raise

    def list_all_users(self, limit, offset, safe = False):

        """
        Returns list of users from db 
        limit -- limit amount of rows returned (int),
        offset -- offset for a query (int)
        safe -- removes private user information from result
        """
        try:

            result = self.get_all_rows(users, USER_FIELDS, limit, offset)
            if safe:
                for key, value in result.items():
                    for field in SECURE_USER_FIELDS:
                        del result[key][field]

                return result
            return result
        except:
            raise

    def get_number_of_users(self):
        """
        Get number of users in database 
        """

        sel = select([func.count(users.c.user_id)])
        try:
            return self.conn.execute(sel).scalar()
        except:
            raise


    def get_user_products(self, uuid):

        """
        Return tuple containing list of all items bought by user 

        Keyword Arguments:
        uuid -- user unique uuid (str)
        
        """

        sel = select([users.c.user_id]).where(users.c.user_uuid == uuid)
        user_id = self.conn.execute(sel).fetchone()[0]
        if not user_id:
            return dict()
        user_products = select([products, bought_products.c.quantity])\
                .select_from(products.join(bought_products))\
                .where(bought_products.c.user_id == user_id)\
                .order_by(desc(bought_products.c.quantity))
        try:
            return self.conn.execute(user_products).fetchall()
        except:
            raise

    def increase_bought_qty(self, amount, id):
        """
        Increases given product quantity
        accepts bought products id, and amount to add

        Keyword Arguments:
        amount -- amount to increase (int),
        id -- unique bought_item primary key (int)
        """
        current = self.conn.execute(select([bought_products.c.quantity])\
                                    .where(bought_products.c.bought_id == id))\
                                    .scalar() # get current amount
        update = bought_products.update()\
                .where(bought_products.c.bought_id == id)\
                .values(quantity = (current + amount))
        trans = self.conn.begin()
        try:
            self.conn.execute(update)
            trans.commit()
        except Exceptions as e:
            logging.error(sys.exc_info()[0])
            trans.rollback()
            raise


    def check_user_bought_product(self, user_uuid, product_uuid):

        """
        Returns Falsy value if user has not bought product with given uuid else returns 
        bought product\'s id
        
        Keyword Arguments:
        user_uuid -- unique user\'s uuid,
        product_uuid -- unique product\'s uuid
        """

        sel = select([users.c.user_id]).where(users.c.user_uuid == user_uuid)

        user = self.conn.execute(sel).fetchone()

        if not user:
            return None

        sel = select([bought_products.c.bought_id]).select_from(products.join(bought_products))\
                .where(and_(products.c.product_uuid == product_uuid,\
                            bought_products.c.user_id == user[0] ))
        try:
            res = self.conn.execute(sel).scalar()
            return res
        except:
            raise

    def create_bought_product(self, qty, user_uuid, product_uuid):

        """
        Create new bought item given product_uuid and user_uuid 
        of product or user with given uuid doesnt exists returns None

        Returns primary_key that has been inserted
        
        Keyword Arguments:
        qty -- amount of items bought (int),
        user_uuid -- unique user uuid (str),
        product_uuid -- unique product uuid (str)
        """
        try:
            user_id = self.conn.execute(select([users.c.user_id])\
                                        .where(users.c.user_uuid == user_uuid)).scalar()
            product_id = self.conn.execute(select([products.c.product_id])\
                                       .where(products.c.product_uuid == product_uuid)).scalar()
        except:
            raise
        if product_id and user_id:
            ins = bought_products.insert()\
                    .values(quantity = qty, user_id = user_id, product_id = product_id)
            trans = self.conn.begin()
            try:
                res = self.conn.execute(ins)
                trans.commit()
                return res.inserted_primary_key[0]
            except Exception as e:
                trans.rollback()
                raise
                logging.error(sys.exc_info[0])
        else:
            return


    def add_bought_product(self, quantity, user_uuid, product_uuid):

        """
        Wrapper for create_bought_product, and increase_bought_quantity,
        if item is already bought by user increase quantity
        else create new record.
        
        Keyword Arguments:
        quantity -- amount of items bought (int),
        user_uuid -- unique user uuid (str),
        product_uuid -- unique product uuid (str)

        """
        try:
            bought = self.check_user_bought_product(user_uuid, product_uuid) # check if user bought item    
        except:
            raise
        if bought:
            try:
                self.increase_bought_qty(quantity, bought) # if yes increase quantity
            except:
                raise
        else:
            try:
                self.create_bought_product(quantity, user_uuid, product_uuid) # else create new record
            except:
                raise

    def _delete_all_users(self):
        """
        Deletes all users from db,
        use at your own risk
        """
        del_all = users.delete()
        self.conn.execute(del_all)

class ProductDatabaseHandler(BaseDBHandler):

    """
    Base class for product database interaction
    accepts optional conn argument which should be a connection object
    to sqlalchemy db
    """

    def __init__(self, *args, **kwargs):

        super(ProductDatabaseHandler, self).__init__(*args, **kwargs)

    def generate_product_uuid(self):
        """
        Generates unique product uuid 
        """
        try:
            res = self.generate_unique_uuid(products.c.product_uuid)
            return res
        except:
            raise

    # not needed
    # def product_exists(self, uuid):
    #     """
    #     Checks if product with given uuid exists in db 
    #     """
    #     return self.check_exists(products.c.product_uuid, uuid)

    def product_unique(self, name):
        """
        Check if product with given name exists in database 
        """
        if not name:
            raise Exception("No product_name given")

        sel = select([exists().where(products.c.product_name == name)])
        try:
            res = self.conn.execute(sel).scalar()
            return not res
        except:
            raise



    def save_product(self, data):
       """
       Create new product with given data

       Returns: primary key of the product that has been inserted
       
       Keyword Arguments:
       data -- dictionary containing product field names,
       must have all the keys in PRODUCT_FIELDS,
       all additional keys all discarded
       """
       els_to_insert = dict()
       if "category" not in data.keys():
           data["category"] = None
       for key, value in data.items():
           if key in PRODUCT_FIELDS:
               els_to_insert[key] = value
       for field in PRODUCT_FIELDS:
           if field not in els_to_insert.keys():
               raise Exception("Data not parsed properly, missing {0}".format(field))
       els_to_insert["product_uuid"] = els_to_insert["uuid"]
       del els_to_insert["uuid"]
       trans = self.conn.begin()
       try:
           res = self.conn.execute(products.insert().values(**els_to_insert))
           trans.commit()
           return res.inserted_primary_key[0]
       except Exception as e:
           trans.rollback()
           logging.error(e)
           raise

    def create_product(self, data):
       """
       Wrapper for creating product
       It:
       -Checks if name is unique
       -Generates unique uuid
       -Saves data to database
       Returns: inserted items pk
       
       Keyword Arguments:
       data -- dictionary containing data to be inserted into database,
       must match fields defined in PRODUCT_FIELDS tuple in config.py
       (minus pk and uuid) (dict)
       See save_product, product_unique and generate_product_uuid 
       for more info
       """
       # put authentication in controller
       # unique = self.product_unique(data["product_name"])
       # if not unique:
       #     raise IntegrityError("Product name must be unique", data["product_name"], "create_product")
       try:
           product_uuid = self.generate_product_uuid()
       except:
           raise
           return
       data["uuid"] = product_uuid
       try:
           res = self.save_product(data)
           return res
       except:
           raise

    def get_number_of_products(self):
        """
        Get total number of products 
        """
        sel = select([func.count(products.c.product_id)])
        try:
            res = self.conn.execute(sel).scalar()
            return res
        except:
            raise


    def get_product(self, uuid):
        """
        Get product with given uuid 
        """
        return self.get_row(products, products.c.product_uuid, uuid)



    def delete_product(self, uuid):
        """
        Delete product with given uuid 
        """
        self.delete_row(products.c.product_uuid, uuid)

    def update_product(self, uuid, data):
        """
        Update product with given uuid 
        
        Keyword Arguments:
        uuid -- string containing unique product uuid (str)
        data -- dictionary containing fields to be updated,
                it is matched against CUSTOM_USER_FIELDS and 
                only those fields specified there will be modified
        """

        items_to_update = dict()
        for key, value in data.items():
            if key in CUSTOM_PRODUCT_FIELDS:
                items_to_update[key] = value
        update_q = products.update().where(products.c.product_uuid == uuid).values(**items_to_update)
        res = self.conn.execute(update_q)
        return res.last_updated_params()


    def get_product_list(self, limit, offset, category = None):
        """
        Get a dictionary of products returned from db 
        Returns: dict
        
        Keyword Arguments:
        limit, offset -- int
        category -- (optional) limits query to given category

        """
        # more specific
        if category:
            sel = select([products])\
            .where(products.c.category == category)\
                    .limit(limit)\
                    .offset(offset)
            res = self.conn.execute(sel).fetchall()
            return self.parse_list_query_data(res, PRODUCT_FIELDS)
        return self.get_all_rows(products, PRODUCT_FIELDS, limit, offset)

    def get_top_selling_products(self, limit=10):
        """
        Returns list of most selled products
        limit -- (optional) limit the results, defaults to 10
        """
        sel = select([products.c.product_name, products.c.product_uuid, func.sum(bought_products.c.quantity).label("sum")])\
                .select_from(products.join(bought_products))\
                .group_by(bought_products.c.product_id)\
                .order_by(desc("sum")).limit(limit)

        top_products = self.conn.execute(sel).fetchall()

        # result = dict()
        # for product_item in top_products:
        #     result[product_item[1]] = product_item[0]
        # return result
        return self.parse_list_query_data(top_products, ("product_name", "product_uuid", "quantity"), "product_name", True)

    def get_all_sold_products(self, limit = None):

        """
        Return list of all items sold 
        limit -- (optional) (int)
        """

        sel = select([products]).select_from(products.join(bought_products)).group_by(bought_products.c.product_id)

        if limit:
            return self.conn.execute(sel.limit(limit)).fetchall()
        else:
            return self.conn.execute(sel).fetchall()

    def _delete_all_products(self):
        """
        Deletes all the products 
        """
        del_all = products.delete()
        self.conn.execute(del_all)

    def _get_all_products(self):
        sel = select([products])
        return self.parse_list_query_data(self.conn.execute(sel), PRODUCT_FIELDS, "product_name")

class AuthDBHandler(object):
    """
    Simple class implementing methods
    related to authenticating users 
    """

    def get_password(self, username, uuid = True):
        """
        Returns hashed password for given identifier
        if uuid is True looks by uuid 
        else looks by username
        """
        if uuid:
            haystack = users.c.user_uuid
        else:
            haystack = users.c.username

        sel = select([users.c.password]).where(haystack == username)
        try:
            res = self.conn.execute(sel).scalar()
            if res:
                return res
            return False
        except:
            raise


