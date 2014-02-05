'''
File: db_base.py
Author: Konrad Wasowicz
Description: BaseDBHandler --- implements basic database interaction methods
'''

import logging
from config import *
from models import users, bought_products, products, engine
from sqlalchemy.sql import select, exists
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy import desc

logging.basicConfig(filename = ROOT_PATH + "/errors.log", level = logging.DEBUG)

class BaseDBHandler(object):


    """
    Implements basic functions for dataabase interactions 
    """


    """
    Returns dictionary containing
    { field_name: value } pairs based on tuple returned from db 
    First argument is a tuple returned from db
    Second argument is a tuple containing fields to be used as keys
    """

    def parse_query_data(self, query, iter):
        if type(iter) not in (tuple, list):
            raise TypeError("iter must be iterable type : list or tuple")
        if not query:
            return dict()
        return dict(zip(iter, query[1:]))

    """
    Same as above but for multiple results 
    """

    def parse_list_query_data(self, data, iter):
        result = dict()
        for row in data:
            temp = self.parse_query_data(row, iter)
            result[temp["uuid"]] = temp
        return result

    """
    Generate unique  uuid 
    for a given table
    field_name argument represents field to check uuid against
    """
    def generate_unique_uuid(self, field_name):
        while True:
            uuid = str(uuid.uuid4())
            sel = select([exists().where(field_name == uuid)])
            result = self.conn.execute(sel).scalar()
            if result == 0:
                return uuid
    
    """
    return unique value represented by uuid 
    """
    def get_row(self, column, uuid, field_tuple):
        sel = select([users]).where(column == uuid)
        q = self.conn.execute(sel).fetchone()
        if not q:
            return dict()
        return self.parse_query_data(q, field_tuple)

    def get_all_rows(self, table, field_tuple, limit, offset):
        sel = select([table]).limit(limit).offset(offset)
        res = self.conn.execute(sel).fetchall()
        return self.parse_list_query_data(res, field_tuple)

    def check_exists(self, column, value):
        sel = select([exists().where(column == value)])
        result = self.conn.execute(sel).scalar()
        return result

    def delete_row(self, column, value):
        delete_q = users.delete().where(column == value)
        self.conn.execute(delete_q)




class UserDatabaseHandler(BaseDBHandler):
        
    def __init__(self, conn = None):
        if conn:
            self.conn = conn

        else:
            self.conn = self.application.conn

    def user_exists(self, uuid):
        return self.check_exists(users.c.user_uuid, uuid)

    def credentials_unique(self, username, email):
        sel = select([exists().where(
                or_(
                    users.c.username == username,
                    users.c.email == email
                )
        )])
        result = self.conn.execute(sel).scalar()
        return not result

    def save_user(self, data, user_fields):
       """
       Accepts dict of elements from a json file 
       """
       els_to_insert = dict()
       for key, value in data.items():
           if key in user_fields:
               els_to_insert[key] = value
       # replace uuid with user_uuid
       for field in user_fields:
           if field not in els_to_insert.keys():
               raise Exception("Data not parsed properly, missing {0}".format(field))
       els_to_insert["user_uuid"] = els_to_insert["uuid"]
       del els_to_insert["uuid"]
       ins = users.insert().values(**els_to_insert)
       self.conn.execute(ins)

    def get_user(self, uuid):
        return self.get_row(users.c.user_uuid, uuid, USER_FIELDS)

    def delete_user(self, uuid):
        self.delete_row(users.c.uuid, uuid)

    def update_user(self, uuid, data):
        items_to_update = dict()
        for key, value in data.items():
            if key in CUSTOM_USER_FIELDS:
                items_to_update[key] = value
        update_q = users.update().where(users.c.user_uuid == uuid).values(**items_to_update)
        self.conn.execute(update_q)

    def list_all_users(self, limit, offset):
        return self.get_all_rows(users, USER_FIELDS, limit, offset)


    def get_user_products(self, uuid):

        sel = select([users.c.user_id]).where(users.c.user_uuid == uuid)
        user_id = self.conn.execute(sel).fetchone()[0]
        if not user_id:
            return dict()
        user_products = select([products, bought_products.c.quantity])\
                .select_from(products.join(bought_products))\
                .where(bought_products.c.user_id == user_id)\
                .order_by(desc(bought_products.c.quantity))

        return self.conn.execute(user_products).fetchall()

    def increase_bought_qty(self, amount, id):
        """
        Increases given product quantity
        accepts bought products id, and amount to add
        """
        current = self.conn.execute(select([bought_products.c.quantity])\
                                    .where(bought_products.c.bought_id == id)).scalar()
        update = bought_products.update()\
                .where(bought_products.c.bought_id == id)\
                .values(quantity = (current + amount))
        self.conn.execute(update)


    def check_user_bought_product(self, user_uuid, product_uuid):

        """
        Returns Falsy value if user has not bought product with given uuid else returns 
        bought product\'s id
        """

        sel = select([users.c.user_id]).where(users.c.user_uuid == user_uuid)

        user = self.conn.execute(sel).fetchone()

        if not user:
            return None

        sel = select([bought_products.c.bought_id]).select_from(products.join(bought_products))\
                .where(and_(products.c.product_uuid == product_uuid,\
                            bought_products.c.user_id == user[0] ))
        res = self.conn.execute(sel).scalar()
        return res

    def create_bought_product(self, qty, user_uuid, product_uuid):
        """
        create new bought item given product_uuid and user_uuid 
        """
        user_id = self.conn.execute(select([users.c.user_id]).where(users.c.user_uuid == user_uuid)).scalar()
        product_id = self.conn.execute(select([products.c.product_id]).where(products.c.product_uuid == product_uuid)).scalar()
        if product_id and user_id:
            ins = bought_products.insert().values(quantity, user_id, product_id)
        else:
            return


    def add_bought_product(self, quantity, user_uuid, product_uuid):

        ## check if user has bought this product already
        bought = self.check_user_bought_product(user_uuid, product_uuid)
        ## if yes increment quantity 
        if bought:
            self.increase_bought_qty(quantity, bought)
        ## else create item
        else:
            self.create_bought_product(quantity, user_uuid, product_uuid)

    def _delete_all_users(self):
        del_all = users.delete()
        self.conn.execute(del_all)

class ProductDatabaseHandler(BaseDBHandler):

    def __init__(self, conn = None):
        if conn:
            self.conn = conn

        else:
            self.conn = self.application.conn

    def generate_product_uuid(self):
        return self.generate_unique_uuid(products.c.product_uuid)


    def product_exists(self, uuid):
        return self.check_exists(products.c.product_uuid, uuid)

    def credentials_unique(self, username, email):
        sel = select([exists().where(
                or_(
                    users.c.username == username,
                    users.c.email == email
                )
        )])
        result = self.conn.execute(sel).scalar()
        return not result

    def save_product(self, data, product_fields):
       els_to_insert = dict()
       for key, value in data.items():
           if key in product_fields:
               els_to_insert[key] = value
       # replace uuid with user_uuid
       for field in product_fields:
           if field not in els_to_insert.keys():
               raise Exception("Data not parsed properly, missing {0}".format(field))
       els_to_insert["product_uuid"] = els_to_insert["uuid"]


    def get_product(self, uuid):
        return self.get_row(products.c.product_uuid, uuid)



    def delete_product(self, uuid):
        self.delete_row(products.c.product_uuid, uuid)

    def update_product(self, uuid, data):

        items_to_update = dict()
        for key, value in data.items():
            if key in CUSTOM_PRODUCT_FIELDS:
                items_to_update[key] = value
        update_q = products.update().where(products.c.product_uuid == uuid).values(**items_to_update)
        self.conn.execute(update_q)


    def list_all_products(self, limit, offset):
        return self.get_all_rows(products, PRODUCT_FIELDS, limit, offset)

    def get_top_selling_products(self, limit=10):
        """
        returns dict containing:
            product_name: amount_sold
        """
        sel = select([func.sum(bought_products.c.quantity).label("suma"), products.c.product_name])\
                .select_from(products.join(bought_products))\
                .group_by(bought_products.c.product_id)\
                .order_by(desc("suma")).limit(limit)

        top_products = self.conn.execute(sel).fetchall()

        result = dict()
        for product_item in top_products:
            result[product_item[1]] = product_item[0]

        return result

    def _delete_all_products(self):
        del_all = products.delete()
        self.conn.execute(del_all)

