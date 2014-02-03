import unittest
import os, sys

sys.path.append("..")
from db_base import BaseDBHandler, UserDatabaseHandler
from config import *

from models import users, products, metadata
from sqlalchemy import create_engine
from sqlalchemy.sql import select
import uuid



class TestDBUtilities(unittest.TestCase):

    def setUp(self):

        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        metadata.create_all()
        self.conn = engine.connect()
        self.db_handler = BaseDBHandler()
        self.uuid1 = str(uuid.uuid4())
        test_user = users.insert().values(user_uuid = self.uuid1, username = u"konrad", password = "deprofundis", email = "depro@depro.com")
        self.conn.execute(test_user)
        self.uuid2 = str(uuid.uuid4())
        test_user2 = users.insert().values(user_uuid = self.uuid2, username = u"malgosia", password = "malgosia", email = "malgosia@gmail.com")
        self.conn.execute(test_user2)

    def tearDown(self):
        metadata.drop_all()



    def test_parsing_database_info(self):

        sel = select([users])
        test_result = self.conn.execute(sel).fetchone()

        res = self.db_handler.parse_query_data(test_result, USER_FIELDS)

        self.assertEquals(dict, type(res))
        self.assertIn("uuid", res)
        self.assertEquals(res["username"], u"konrad")
        self.assertEquals(res["email"], "depro@depro.com")
        self.assertEquals(res["password"], "deprofundis")

        empty_test = self.db_handler.parse_query_data(list(), USER_FIELDS)
        self.assertFalse(empty_test)
        self.assertEquals(empty_test, dict())


        self.assertRaises(TypeError, lambda: self.db_handler.parse_query_data(list(), dict()))
        self.assertRaises(TypeError, lambda: self.db_handler.parse_query_data(list()))
        self.assertRaises(TypeError, lambda: self.db_handler.parse_query_data(list(), None))

    def test_multiple_queries_parsing(self):
        sel = select([users])
        test_result = self.db_handler.parse_list_query_data(self.conn.execute(sel).fetchall(), USER_FIELDS)
        self.assertEquals(2, len(test_result))
        self.assertIn(self.uuid1, test_result)
        self.assertEquals(u"malgosia", test_result[self.uuid2]["username"])

    def test_user_methods(self):

        self.user_handler = UserDatabaseHandler(conn = self.conn)

        #test unique user uuid

        self.assertTrue(self.user_handler.user_exists(self.uuid1))
        self.assertFalse(self.user_handler.user_exists(str(uuid.uuid4())))
        
        #test unique username or password
        self.assertFalse(self.user_handler.credentials_unique(u"konrad", "test@test.com"))
        self.assertTrue(self.user_handler.credentials_unique(u"konrad2", "test@test.com"))
        self.assertFalse(self.user_handler.credentials_unique(u"konrad2", "depro@depro.com"))
        self.assertFalse(self.user_handler.credentials_unique(u"konrad", "depro@depro.com"))

    def test_adding_user(self):

        self.user_handler = UserDatabaseHandler(conn = self.conn)

        data = dict(
            uuid = str(uuid.uuid4()),
            username = u"test_user",
            password = "testpassword",
            email = "test@test.com"
                   )

        self.user_handler.save_user(data, USER_FIELDS)
        sel = select([users]).where(users.c.username == u"test_user")
        added_user = self.conn.execute(sel).fetchone()
        self.assertTrue(added_user)
        # test id
        self.assertEquals(3, added_user[0])
        self.assertEquals("test@test.com", added_user[4])


        #TODO think about replacing generic uuid with user_uuid in user_fields
        #TODO also implement validators to be called before insert





if __name__ == "__main__":
    unittest.main()

