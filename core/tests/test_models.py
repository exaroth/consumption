import os, sys
import unittest
from sqlalchemy import create_engine
from sqlalchemy.sql import select, exists
import uuid

sys.path.append("..")

from models import users, bought_products, products, metadata


class BaseDatabaseHandler(unittest.TestCase):


    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        metadata.create_all()
        self.conn = engine.connect()

    def tearDown(self):
        metadata.drop_all()


class TestBasicUserOperations(BaseDatabaseHandler):


    def setUp(self):
        super(TestBasicUserOperations, self).setUp()
        self.sample_uuid1 = str(uuid.uuid4())
        self.sample_uuid2 = str(uuid.uuid4())
        self.sample_uuid3 = str(uuid.uuid4())

        ins = users.insert().values(user_uuid = self.sample_uuid1, username = u"konrad", password = "test", email = "depro@depro.com")
        self.conn.execute(ins)
        ins = users.insert().values(user_uuid = self.sample_uuid2, username = u"malgosia", password = "test2", email = "malgosia@depro.com")
        self.conn.execute(ins)
        ins = users.insert().values(user_uuid = self.sample_uuid3, username = u"kuba", password = "test3", email = "kuba@depro.com")
        self.conn.execute(ins)

    def test_getting_user_info(self):
        sel = select([users]).where(users.c.username == u"konrad")

        row = self.conn.execute(sel).fetchone()

        self.assertEquals(u"konrad", row[2])
        self.assertEquals(1, row[0], "check if user_id == 1")
        self.assertEquals("test", row[3])

        sel = select([users.c.user_uuid]).where(users.c.username == u"malgosia")
        row = self.conn.execute(sel).fetchone()

        self.assertEquals(self.sample_uuid2, row[0])

    def test_uniqueness(self):

        # check unique uuid
        ins = users.insert().values(user_uuid = self.sample_uuid1, username = u"test", password = "test", email = "test@test.com")
        self.assertRaises(self.conn.execute(ins))

        #check unique username
        ins = users.insert().values(user_uuid = str(uuid.uuid4()), username = u"konrad", password = "test_pass", email = "test@test.com")
        self.assertRaises(self.conn.execute(ins))

        #check unique email
        ins = users.insert().values(user_uuid = str(uuid.uuid4()), username = u"test", password = "test", email = "depro@depro.com" )
        self.assertRaises(self.conn.execute(ins))


    def test_inserting_empty_values(self):
        ins = users.insert().values(user_uuid = "", username = u"test", password = "test_pass", email = "test@tes.com")
        self.assertRaises(self.conn.execute(ins))
        ins = users.insert().values(user_uuid = str(uuid.uuid4()), username = u"", password = "test_pass", email = "test@tes.com")
        self.assertRaises(self.conn.execute(ins))


    def test_updating(self):

        up = users.update().where(users.c.username == u"konrad").values(email = "zmieniony@depro.com")
        self.conn.execute(up)
        sel = select([users]).where(users.c.username == u"konrad")
        res = self.conn.execute(sel).fetchone()
        self.assertEquals(res[4], "zmieniony@depro.com")

        #check updating with empyt value doenst work
        
        #!!TODO - implement validator
        up = users.update().where(users.c.username == u"konrad").values(email = "")
        self.conn.execute(up)

    def test_deleting(self):

        d = users.delete().where(users.c.user_uuid == self.sample_uuid1)
        self.conn.execute(d)
        sel = self.conn.execute(select([users]).where(users.c.username == u"konrad")).fetchone()
        #Empty tuple
        self.assertFalse(sel)

class TestBasicProductOperations(BaseDatabaseHandler):

    def setUp(self):
        super(TestBasicProductOperations, self).setUp()
        self.sample_uuid1 = str(uuid.uuid4())
        self.sample_uuid2 = str(uuid.uuid4())
        self.sample_uuid3 = str(uuid.uuid4())
        product1 = products.insert().values(product_uuid = self.sample_uuid1, product_name = u"wiertarka", product_desc = u"zajebista wiertarka kuptokuptokupto")
        self.conn.execute(product1)
        product2 = products.insert().values(product_uuid = self.sample_uuid2, product_name = u"wiertarkowkretarka", product_desc = u"zajefajniebista wkretarka I WIERTARKA to tez kup glabie")
        self.conn.execute(product2)
        product3 = products.insert().values(product_uuid = self.sample_uuid3, product_name = u"wiertarkowkretarkowrzucarka", product_desc = u"No comment, just buy it")
        self.conn.execute(product3)

    def test_uniqueness(self):
        
        #uuid
        ins = products.insert().values(product_uuid = self.sample_uuid1, product_name = u"mlot kowalski", product_desc = u"mlot nic dodac nic ujac")
        self.assertRaises(self.conn.execute(ins))
        #product_name
        ins = products.insert().values(product_uuid = str(uuid.uuid4()), product_name = u"wiertarka", product_desc = u"test")
        self.assertRaises(self.conn.execute(ins))

class TestBoughtProductsOperations(BaseDatabaseHandler):

    def setUp(self):
        super(TestBoughtProductsOperations, self).setUp()
        self.sample_uuid1 = str(uuid.uuid4())
        self.sample_uuid2 = str(uuid.uuid4())
        self.sample_uuid3 = str(uuid.uuid4())

        ins = users.insert().values(user_uuid = self.sample_uuid1, username = u"konrad", password = "test", email = "depro@depro.com")
        self.conn.execute(ins)
        ins = users.insert().values(user_uuid = self.sample_uuid2, username = u"malgosia", password = "test2", email = "malgosia@depro.com")
        self.conn.execute(ins)
        ins = users.insert().values(user_uuid = self.sample_uuid3, username = u"kuba", password = "test3", email = "kuba@depro.com")
        self.conn.execute(ins)

        ins = products.insert().values(product_uuid = str(uuid.uuid4()), product_name = u"siekiera", product_desc = u"siekierezada...dobry film")
        self.conn.execute(ins)

        ins = products.insert().values(product_uuid = str(uuid.uuid4()), product_name = u"pila mechaniczna", product_desc = u"masakra")
        self.conn.execute(ins)

        ins = products.insert().values(product_uuid = str(uuid.uuid4()), product_name = u"wykalaczka", product_desc = u"do zebow")
        self.conn.execute(ins)


    def test_adding_product_to_user(self):

        #Konrad kupuje siekiere w sklepie w wiadomym celu

        sel = select([users]).where(users.c.username == u"konrad")
        konrad = self.conn.execute(sel).fetchone()

        sel = select([products]).where(products.c.product_name == u"siekiera")
        siekiera = self.conn.execute(sel).fetchone()

        add_siekiera = bought_products.insert().values(quantity = 1, user_id = konrad[0], product_id = siekiera[0])

        self.conn.execute(add_siekiera)


        # Different sytax to handle multiple connections
        all = list(bought_products.select().execute())

        self.assertEquals(1, len(all))
        
        #check id
        self.assertEquals(1, all[0][0])

        #check user
        self.assertEquals(konrad[0], all[0][2])

        #check product
        self.assertEquals(siekiera[0], all[0][3])

        #check quantity
        self.assertEquals(1, all[0][1])

        #Dodaj 10 wykalaczek

        ins = bought_products.insert().values(quantity = 10, user_id = konrad[0], product_id = 1)
        self.conn.execute(ins)


        # Get Konrad items

        ins = select([bought_products]).select_from(users.join(bought_products) )
        res = list(self.conn.execute(ins).fetchall())

        second_item = res[1]

        self.assertEquals(2, second_item[0])
        self.assertEquals(10, second_item[1])
        self.assertEquals(1, second_item[2])

    def test_deleting_products(self):

        """
        Note this doenst work in sqlite 
        """
        #TODO

        sel = select([users]).where(users.c.username == u"konrad")
        konrad = self.conn.execute(sel).fetchone()

        sel = select([products]).where(products.c.product_name == u"siekiera")
        siekiera = self.conn.execute(sel).fetchone()

        add_siekiera = bought_products.insert().values(quantity = 1, user_id = konrad[0], product_id = siekiera[0])

        self.conn.execute(add_siekiera)
        ins = bought_products.insert().values(quantity = 10, user_id = konrad[0], product_id = 1)
        self.conn.execute(ins)
        sel = select([bought_products])
        res = list(self.conn.execute(sel).fetchall())
        print res

        d = products.delete().where(products.c.product_name == u"wykalaczka")
        self.conn.execute(d)

        sel = select([bought_products])
        res = list(self.conn.execute(sel).fetchall())









if __name__ == "__main__":
    unittest.main()








