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
        if not tuple or type(iter) not in (tuple, list):
            raise TypeError("iter must be iterable type : list or tuple")
        if query is None:
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





class UserDatabaseHandler(BaseDBHandler):
        
    def __init__(self, conn = None):
        if conn:
            self.conn = conn

        else:
            self.conn = self.application.conn

    """
    Generate unique user uuid 
    """
    def generate_user_uuid(self):

        while True:
            user_uuid = str(uuid.uuid4())
            sel = select([exists().where(users.c.user_uuid == user_uuid)])
            result = self.conn.execute(sel).scalar()
            if result == 0:
                return user_uuid


    def user_exists(self, uuid):
        sel = select([exists().where(users.c.user_uuid == uuid)])
        result = self.conn.execute(sel).scalar()
        return result

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
        sel = select([users]).where(users.c.user_uuid == uuid)
        q = self.conn.execute(sel).fetchone()
        return self.parse_query_data(q, USER_FIELDS)

    def delete_user(self, uuid):
        delete_q = users.delete().where(users.c.user_uuid == uuid)
        self.conn.execute(delete_q)

    def update_user(self, uuid, data):
        items_to_update = dict
        for key, value in data.items():
            if key in CUSTOM_USER_FIELDS:
                items_to_update[key] = value
        update_q = users.update().where(users.c.user_uuid == uuid).values(**items_to_update)
        self.conn.execute(update_q)


    def list_all_users(self, limit, offset):
        sel = select([users]).limit(limit).offset(offset)
        res = self.conn.execute(sel).fetchall()
        return self.parse_list_query_data(res, USER_FIELDS)

