import unittest
import os, sys
import uuid

sys.path.append("..")
from db_base import BaseDBHandler, UserDatabaseHandler, ProductDatabaseHandler
from config import *

from models import users, products, metadata, bought_products
from sqlalchemy import create_engine
from sqlalchemy.sql import select, exists

from sqlalchemy import distinct, func
from sqlalchemy.exc import IntegrityError



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

        # test unique user uuid
        # removed user_exists (not needed)

        # self.assertTrue(self.user_handler.user_exists(self.uuid1))
        # self.assertFalse(self.user_handler.user_exists(str(uuid.uuid4())))

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

        self.user_handler.save_user(data)
        sel = select([users]).where(users.c.username == u"test_user")
        added_user = self.conn.execute(sel).fetchone()
        self.assertTrue(added_user)
        # test id
        self.assertEquals(3, added_user[0])
        self.assertEquals("test@test.com", added_user[4])


        #TODO think about replacing generic uuid with user_uuid in user_fields
        #TODO also implement validators to be called before insert

        #test adding with not enough fields

        data = dict(
            uuid = str(uuid.uuid4()),
            password = "testpassword",
        )

        self.assertRaises(lambda: self.user_handler.save_user(data))

        #test adding with too many fields doesnt raise an error
        data = dict(
            uuid = str(uuid.uuid4()),
            username = u"test_user2",
            password = "testpassword",
            email = "test@test2.com",
            some_crappy_fields = "crapcrapcrap"
        )
        self.user_handler.save_user(data)
        sel = select([exists().where(users.c.username == u"test_user2")])
        added_user = self.conn.execute(sel).scalar()
        self.assertTrue(added_user)

    def test_getting_single_user_info(self):

        self.user_handler = UserDatabaseHandler(conn = self.conn)
        single_user = self.user_handler.get_user(self.uuid1)
        self.assertEquals(dict, type(single_user))
        self.assertIn("username", single_user.keys())
        self.assertNotIn("id", single_user.keys())
        self.assertEquals(u"konrad", single_user["username"])
        nonexistent = self.user_handler.get_user(str(uuid.uuid4()))
        self.assertEquals(dict, type(nonexistent))
        self.assertEquals(0, len(nonexistent))

    def test_updating_user_data(self):

        self.user_handler = UserDatabaseHandler(conn = self.conn)

        update_data = dict(
            email = "zmieniony@gmail.com",
            username = "tosieniezmieni",
            password = "zmieniony"
        )

        self.user_handler.update_user(self.uuid1, update_data)

        sel = select([users]).where(users.c.user_id == 1)
        updated_user = list(self.conn.execute(sel))[0]
        self.assertEquals(u"konrad", updated_user[2])
        self.assertEquals("zmieniony", updated_user[3])
        self.assertEquals("zmieniony@gmail.com", updated_user[4])

class TestProductsDB(unittest.TestCase):

    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        metadata.create_all()
        self.conn = engine.connect()
        self.product_handler = ProductDatabaseHandler(self.conn)

    def tearDown(self):
        metadata.drop_all()


    def test_saving_a_product(self):

        data = dict(uuid = str(uuid.uuid4()), product_name = u"nowy", product_desc = u"nowy produkt" )

        inserted_id = self.product_handler.save_product(data)
        self.assertEquals(1, inserted_id)
        sel = select([products])
        prod = self.conn.execute(sel).fetchone()
        self.assertTrue(prod)
        self.assertEquals(prod[2], u"nowy")
        self.assertEquals(prod[3], u"nowy produkt")

        pr_uuid = str(uuid.uuid4())

        data = dict(uuid = pr_uuid, product_name = u"nowy2", product_desc = u"drugi nowy produkt" )
        inserted_id = self.product_handler.save_product(data)
        self.assertEquals(2, inserted_id)

        sel = select([products])
        product_list = self.conn.execute(sel).fetchall()
        self.assertEquals(2, len(product_list))
        sec = product_list[1]
        self.assertEquals(u"nowy2", sec[2])
        self.assertEquals(u"drugi nowy produkt", sec[3])

        # test wrong data

        # missing fields

        data = dict(product_name = u"nowy3", product_desc = u"trzeci")
        self.assertRaises(lambda: self.product_handler.save_product(data))

        data = dict(uuid = str(uuid.uuid4()), product_name = u"nowy4")
        self.assertRaises(lambda: self.product_handler.save_product(data))
        # not unique



        # TODO integrity error not risen, even though it says so
        data = dict(uuid = pr_uuid, product_name = u"nowy5", product_desc = u"random")
        self.assertRaises(self.product_handler.save_product(data))
        sel = select([products])
        # print self.conn.execute(sel).fetchall()
                
        # TODO unique contraint not working natively (probably because of sqlite)
        data = dict(uuid = str(uuid.uuid4()), product_name = u"nowy", product_desc = u"t")
        self.product_handler.save_product(data)
    def test_checking_if_product_unique(self):

        data = dict(uuid = str(uuid.uuid4()), product_name = u"nowy", product_desc = u"nowy produkt" )
        self.product_handler.save_product(data)

        self.assertFalse(self.product_handler.product_unique(u"nowy"))
        # self.assertFalse(self.product_handler.product_unique("nowy")) # checking if works for ascii too
        self.assertTrue(self.product_handler.product_unique(u"nowy_2"))

    def test_create_product_wrapper(self):
        data = dict(product_name = u"inserted", product_desc = u"sample")
        product_id = self.product_handler.create_product(data)
        self.assertEquals(1, product_id)
        sel = select([products])
        res = self.conn.execute(sel).fetchall()
        self.assertEquals(1, len(res))
        new_product = res[0]
        self.assertEquals(u"inserted", new_product[2])

        data = dict(product_name = u"inserted2", product_desc = u"sample")
        product_id2 = lambda: self.product_handler.create_product(data)
        self.assertEquals(product_id2(), 2)
        sel = select([products])
        res = tuple(self.conn.execute(sel)) # wrapper used to prevent locking the table

        self.assertEquals(2, len(res))
        new_product2 = res[1]

        self.assertEquals(u"inserted2", new_product2[2])

        # test wrong data insertions

        data = dict(product_name = u"inserted", product_desc = u"x")
        self.assertRaises(lambda : self.product_handler.create_product(data))
        sel = select([products])
        res = tuple(self.conn.execute(sel)) # wrapper used to prevent locking the table

        self.assertEquals(2, len(res))

        # test with too many arguments

        data = dict(product_name = u"deprofundis", product_desc = u"error", random_arg = 10)
        ins = self.product_handler.create_product(data)
        self.assertEquals(3, ins)

        res = self.product_handler._get_all_products()
        self.assertEquals(3, len(res))
        self.assertIn(u"deprofundis", res)
        self.assertEquals(res["deprofundis"]["product_desc"], u"error")
        self.assertNotIn("random_arg", res["deprofundis"].keys())

    def test_getting_top_products(self):

        data = dict(product_name = u"wiertarka", product_desc = u"test")
        p1 = self.product_handler.create_product(data)

        data = dict(product_name = u"suszarka", product_desc = u"test")
        p2 = self.product_handler.create_product(data)
        

        data = dict(product_name = u"miotla", product_desc = u"test")
        p3 = self.product_handler.create_product(data)

        self.user_handler = UserDatabaseHandler(conn = self.conn)

        data = dict(username = u"konrad", password = "test", email = "konrad@gmail.com")
        u1 = self.user_handler.create_user(data)

        data = dict(username = u"malgosia", password = "test", email = "malgosia@gmail.com")
        u2 = self.user_handler.create_user(data)

        data = dict(username = u"kuba", password = "test", email = "kuba@gmail.com")
        u3 = self.user_handler.create_user(data)

        sel = select([users.c.user_uuid]).where(users.c.user_id == u1)
        user1 = self.conn.execute(sel).scalar()

        sel = select([users.c.user_uuid]).where(users.c.user_id == u2)
        user2 = self.conn.execute(sel).scalar()

        sel = select([users.c.user_uuid]).where(users.c.user_id == u3)
        user3 = self.conn.execute(sel).scalar()

        sel = select([products.c.product_uuid]).where(products.c.product_id == p1)
        pr1 = self.conn.execute(sel).scalar()

        sel = select([products.c.product_uuid]).where(products.c.product_id == p2)
        pr2 = self.conn.execute(sel).scalar()

        sel = select([products.c.product_uuid]).where(products.c.product_id == p3)
        pr3 = self.conn.execute(sel).scalar()

        self.user_handler.add_bought_product(10, user1, pr1)
        self.user_handler.add_bought_product(12, user1, pr2)
        self.user_handler.add_bought_product(18, user1, pr3)
        self.user_handler.add_bought_product(2, user2, pr1)
        self.user_handler.add_bought_product(18, user2, pr2)
        self.user_handler.add_bought_product(1, user2, pr3)
        self.user_handler.add_bought_product(2, user3, pr1)
        self.user_handler.add_bought_product(5, user3, pr2)
        self.user_handler.add_bought_product(9, user3, pr3)

        #TODO



class TestBoughtProductsDB(unittest.TestCase):

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
        self.uuid3 = str(uuid.uuid4())
        test_user3 = users.insert().values(user_uuid = self.uuid3, username = u"kuba", password = "kuba", email = "kuba@gmail.com")
        self.conn.execute(test_user3)

        self.product_uuid1 = str(uuid.uuid4())
        self.product_uuid2 = str(uuid.uuid4())
        self.product_uuid3 = str(uuid.uuid4())

        product_1 = products.insert().values(product_uuid = self.product_uuid1, product_name = u"wiertarka", product_desc = u"test" )
        self.conn.execute(product_1)
        product_2 = products.insert().values(product_uuid = self.product_uuid2, product_name = u"suszarka", product_desc = u"test" )
        self.conn.execute(product_2)
        product_3 = products.insert().values(product_uuid = self.product_uuid3, product_name = u"pralka", product_desc = u"test" )
        self.conn.execute(product_3)

        buyout1 = bought_products.insert().values(quantity = 10, user_id = 1, product_id = 1)
        self.conn.execute(buyout1)
        buyout2 = bought_products.insert().values(quantity = 5, user_id = 1, product_id = 2)
        self.conn.execute(buyout2)
        buyout3 = bought_products.insert().values(quantity = 1, user_id = 1, product_id = 3)
        self.conn.execute(buyout3)


        buyout4 = bought_products.insert().values(quantity = 11, user_id = 2, product_id = 1)
        self.conn.execute(buyout4)
        buyout5 = bought_products.insert().values(quantity = 1, user_id = 2, product_id = 2)
        self.conn.execute(buyout5)
        buyout6 = bought_products.insert().values(quantity = 2, user_id = 3, product_id = 1)
        self.conn.execute(buyout6)

    def tearDown(self):
        metadata.drop_all()

    def test_getting_all_user_products(self):

        self.user_handler = UserDatabaseHandler(conn = self.conn)
        

        konrad_products = self.user_handler.get_user_products(str(self.uuid1))
        self.assertEquals(3, len(konrad_products))
        self.assertEquals(10, konrad_products[0][len(konrad_products[0]) - 1])
        bought_fields = PRODUCT_FIELDS + ("quantity", )

        parsed_input = self.user_handler.parse_list_query_data(konrad_products, bought_fields)

        self.assertIn(self.product_uuid1, parsed_input)
        self.assertEquals(parsed_input[self.product_uuid1]["product_name"], u"wiertarka")
        malgosia_products = self.user_handler.get_user_products(self.uuid2)
        self.assertEquals(2, len(malgosia_products))

        parsed_malgosia = self.user_handler.parse_list_query_data(malgosia_products, bought_fields)
        self.assertNotIn(self.product_uuid3, parsed_malgosia)
        self.assertEquals(11, parsed_malgosia[self.product_uuid1]["quantity"])



    def test_checking_if_user_has_bought_product(self):


        self.user_handler = UserDatabaseHandler(conn = self.conn)

        self.assertTrue(self.user_handler.check_user_bought_product(self.uuid1, self.product_uuid1))
        self.assertFalse(self.user_handler.check_user_bought_product(self.uuid2, self.product_uuid3))
        self.assertEquals(1, self.user_handler.check_user_bought_product(self.uuid1, self.product_uuid1))
        self.assertEquals(2, self.user_handler.check_user_bought_product(self.uuid1, self.product_uuid2))

        self.assertFalse(self.user_handler.check_user_bought_product(self.uuid3, self.product_uuid2))
        self.assertFalse(self.user_handler.check_user_bought_product(self.uuid3, self.product_uuid3))
        self.assertTrue(self.user_handler.check_user_bought_product(self.uuid3, self.product_uuid1))
        self.assertEquals(4, self.user_handler.check_user_bought_product(self.uuid2, self.product_uuid1))

        self.assertFalse(self.user_handler.check_user_bought_product(str(uuid.uuid4()), self.product_uuid1))
        self.assertFalse(self.user_handler.check_user_bought_product(self.uuid1, str(uuid.uuid4())))

    def test_increasing_item_quantity(self):

        self.user_handler = UserDatabaseHandler(conn = self.conn)

        # konrad buys 1 product
        self.user_handler.increase_bought_qty(1, 1)
        sel = select([bought_products.c.quantity]).where(bought_products.c.bought_id == 1)
        val = self.conn.execute(sel).scalar()

        self.assertEquals(11, val)
        
        # and 4 more
        self.user_handler.increase_bought_qty(4, 1)
        sel = select([bought_products.c.quantity]).where(bought_products.c.bought_id == 1)
        val = self.conn.execute(sel).scalar()

        self.assertEquals(15, val)


        self.user_handler.increase_bought_qty(2, 4)
        sel = select([bought_products.c.quantity]).where(bought_products.c.bought_id == 4)
        val = self.conn.execute(sel).scalar()

        self.assertEquals(13, val)


    def test_creating_new_bought_item(self):
        
        new_uuid = str(uuid.uuid4())
        new_product = products.insert().values(product_uuid = new_uuid, product_name = u"hantle", product_desc = u"test" )
        self.conn.execute(new_product)


        self.user_handler = UserDatabaseHandler(conn = self.conn)

        # Konrad buys 10 hantle items
        self.user_handler.create_bought_product(10, self.uuid3, new_uuid )

        sel = select([products]).select_from(products.join(bought_products).join(users)).group_by(bought_products.c.product_id)
        konrad_items = self.conn.execute(sel).fetchall()
        self.assertEquals(4, len(konrad_items))
        self.assertEquals(u"hantle", konrad_items[len(konrad_items) - 1][2])

        # test for nonexistent user

        empty = self.user_handler.create_bought_product(20, str(uuid.uuid4()), new_uuid)

        self.assertFalse(empty)

        # test for nonexistent item

        empty = self.user_handler.create_bought_product(20, self.uuid1, str(uuid.uuid4()))
        self.assertFalse(empty)


    def test_adding_bought_product_function(self):

        new_uuid = str(uuid.uuid4())
        new_product = products.insert().values(product_uuid = new_uuid, product_name = u"hantle", product_desc = u"test" )
        self.conn.execute(new_product)

        self.user_handler = UserDatabaseHandler(conn = self.conn)
        

        #test adding new item

        self.user_handler.add_bought_product(10, self.uuid1, new_uuid)
        sel = select([products]).select_from(products.join(bought_products).join(users)).group_by(bought_products.c.product_id)
        konrad_items = self.conn.execute(sel).fetchall()
        self.assertEquals(4, len(konrad_items))
        self.assertEquals(u"hantle", konrad_items[len(konrad_items) - 1][2])

        bought_id = self.user_handler.check_user_bought_product(self.uuid1, new_uuid)
        self.assertTrue(bought_id)

        bought_quantity = select([bought_products.c.quantity]).where(bought_products.c.bought_id == bought_id)
        q = self.conn.execute(bought_quantity).scalar()
        self.assertEquals(q, 10)


        # test increasing quantity of item already on the list


        self.user_handler.add_bought_product(2, self.uuid1, new_uuid)


        bought_id = self.user_handler.check_user_bought_product(self.uuid1, new_uuid)
        self.assertTrue(bought_id)

        sel = select([products]).select_from(products.join(bought_products).join(users)).group_by(bought_products.c.product_id)
        konrad_items = self.conn.execute(sel).fetchall()
        self.assertEquals(4, len(konrad_items))
        bought_quantity = select([bought_products.c.quantity]).where(bought_products.c.bought_id == bought_id)
        q = self.conn.execute(bought_quantity).scalar()
        self.assertEquals(q, 12)






if __name__ == "__main__":
    unittest.main()

