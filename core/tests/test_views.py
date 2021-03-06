from tornado.testing import AsyncHTTPTestCase
import tornado.testing
import os, sys
import simplejson as json


sys.path.append("..")

from views import Application

from models import users, bought_products, products, engine, metadata
from sqlalchemy import create_engine
from sqlalchemy.sql import select
import uuid


class TestUserOperations(AsyncHTTPTestCase):

    def get_app(self):
        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        self.conn = engine.connect()
        metadata.create_all()
        return Application(self.conn)

    def tearDown(self):
        metadata.drop_all()
        


    def test_saving_user_method(self):


        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )

        resp = self.fetch("/users", method = "POST", body = json.dumps(data))

        self.assertIn("201", resp.body)
        self.assertEquals(201, resp.code)

        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )


        resp = self.fetch("/users", method = "POST", body = json.dumps(data))
        self.assertIn("201", resp.body)
        self.assertIn("Created", resp.body)

        # test unique username and password

        # username

        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia2@gmail.com")


        resp = self.fetch("/users", method = "POST", body = json.dumps(data))
        self.assertIn("Username and password have to be unique", resp.body)
        self.assertEquals(400, resp.code)

        # email

        data = dict()
        data["user"] = dict(
            username = u"malgosia2",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )

        resp = self.fetch("/users", method = "POST", body = json.dumps(data))
        self.assertIn("Username and password have to be unique", resp.body)
        self.assertEquals(400, resp.code)

        # test for missing fields

        data["user"] = dict(
            username = u"kuba",
            password = "kuba"

        )
        resp = self.fetch("/users", method = "POST", body = json.dumps(data))

        self.assertEquals(400, resp.code)
        self.assertIn("Missing fields", resp.body)



        data["user"] = dict(
            username = u"kuba",
            email = "kuba@gmail.com"
        )


        resp = self.fetch("/users", method = "POST", body = json.dumps(data))

        self.assertEquals(400, resp.code)
        self.assertIn("Missing fields", resp.body)

    def test_getting_user_list(self):

        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = u"kuba",
            password = "kuba",
            email = "kuba@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        resp = self.fetch("/users", method = "GET")
        self.assertIn("konrad", resp.body)
        self.assertIn("kuba", resp.body)
        self.assertIn("malgosia", resp.body)
        self.assertEquals(200, resp.code)
        self.assertIn("application/json", resp.headers.values())

        dump = json.loads(resp.body)

        self.assertEquals(3, dump["_metadata"]["total"])
        self.assertEquals(3, len(dump["users"]))

    def test_getting_single_user_info(self):
        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        sel = select([users.c.user_uuid]).where(users.c.username == "konrad")
        konrad_uuid = self.conn.execute(sel).scalar()

        res = self.fetch("/user?id="+konrad_uuid , method = "GET")
        self.assertEquals(200, res.code)
        self.assertIn("konrad", res.body)
        self.assertNotIn("password", res.body)
        self.assertNotIn("deprofundis", res.body)
        nonexistent = str(uuid.uuid4())
        res = self.fetch("/user?id="+nonexistent, method = "GET")
        self.assertEquals(404, res.code)
        self.assertIn("Not_Found", res.body)
        # test getting information on authenticated user
        user_data = self.fetch("/user?id=konrad&password=deprofundis&direct=1", method = "GET")
        self.assertEquals(user_data.code, 200)
        self.assertIn("password", user_data.body)
        self.assertIn("konrad", user_data.body)
        # remote get
        user_data = self.fetch("/user?id=" + konrad_uuid + "&password=deprofundis&direct=0", method = "GET")
        self.assertEquals(user_data.code, 200)
        self.assertIn("password", user_data.body)
        self.assertIn("konrad", user_data.body)
        # direct with no password
        user_data = self.fetch("/user?id=konrad&direct=1", method = "GET")
        self.assertEquals(user_data.code, 200)
        self.assertIn("konrad", user_data.body)
        self.assertNotIn("password", user_data.body)
        # direct with nonexistent account
        user_data = self.fetch("/user?id=nonexistent&direct=1")
        self.assertEquals(user_data.code, 404)
        self.assertIn("User doesnt exist", user_data.body)
        # password with nonexxistent
        user_data = self.fetch("/user?id=nonexistent&password=test")
        self.assertEquals(404, user_data.code)
        # all with nonexistent
        user_data = self.fetch("/user?id=nonexistent&password=test&direct=1")
        self.assertEquals(404, user_data.code)
        user_data = self.fetch("/user?id=nonexistent&password=test&direct=0")
        self.assertEquals(404, user_data.code)

    def test_updating_user_info(self):
        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["update"] = dict(
            password = "depro",
            email = "zmieniony@gmail.com"
        )
        resp = self.fetch("/user?username=konrad&password=deprofundis", method = "PUT", body= json.dumps(data))
        self.assertEquals(201, resp.code)
        self.assertIn("zmieniony@gmail.com", resp.body)
        self.assertIn("password", resp.body)
        # test wrong password
        resp = self.fetch("/user?username=konrad&password=nieprawidlowy", method = "PUT", body= json.dumps(data))
        self.assertEquals(403, resp.code)
        # test wrong username
        resp = self.fetch("/user?username=nieprawidlowy&password=nieprawidlowy", method = "PUT", body= json.dumps(data))
        self.assertEquals(403, resp.code)
        # test providing additional data
        data["update"] = dict(
            email = "crap@gmail.com",
            somecrap = "crapcrapcrap"
        )
        resp = self.fetch("/user?username=konrad&password=depro", method = "PUT", body= json.dumps(data))
        self.assertEquals(201, resp.code)
        self.assertIn("crap@gmail.com", resp.body)
        # test providing no data
        data = dict()
        resp = self.fetch("/user?username=konrad&password=depro", method = "PUT", body= json.dumps(data))
        self.assertEquals(304, resp.code)

    def test_deleting_users(self):
        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )

        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        resp = self.fetch("/user?id=konrad&password=deprofundis", method = "DELETE")

        self.assertEquals(200, resp.code )

        sel = select([users])
        res = self.conn.execute(sel).fetchall()
        self.assertEquals(1, len(res))

        resp = self.fetch("/users")
        self.assertNotIn("konrad", resp.body)


        resp = self.fetch("/user?id=malgosia&password=malgosia", method = "DELETE")

        sel = select([users])
        res = self.conn.execute(sel).fetchall()
        self.assertEquals(0, len(res))

        resp = self.fetch("/users")
        self.assertNotIn("malgosia", resp.body)

        # test for invalid credentials
        data = dict()
        data["user"] = dict(
            username = u"malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        # username

        resp = self.fetch("/user?id=invalid&password=malgosia", method = "DELETE")
        self.assertEquals(403, resp.code )

        # password

        resp = self.fetch("/user?id=malgosia&password=invalid", method = "DELETE")
        self.assertEquals(403, resp.code )

        # not enought data

        resp = self.fetch("/user?id=malgosia", method = "DELETE")
        self.assertEquals(403, resp.code )

        resp = self.fetch("/user", method = "DELETE")
        self.assertEquals(403, resp.code )



class TestProductOperations(AsyncHTTPTestCase):

    def get_app(self):
        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        self.conn = engine.connect()
        metadata.create_all()
        return Application(self.conn)

    def tearDown(self):
        metadata.drop_all()


    def test_inserting_products(self):
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "wruumm",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        sel = select([products])

        res = self.conn.execute(sel).fetchall()
        self.assertEquals(1, len(res))
        self.assertIn("wiertarka", list(res[0]))
        self.assertIn("konrad", list(res[0]))
        self.assertIn("wruumm", list(res[0]))



        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "telewizor",
            product_desc = "pierdoly",
            price = "1200zl",
            category = "rtv"
        )

        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))

        res = self.conn.execute(sel).fetchall()
        self.assertEquals(2, len(res))

        tv = list(res[1])
        
        self.assertIn("telewizor", tv)
        self.assertIn("pierdoly", tv)
        self.assertIn("1200zl", tv)
        self.assertIn("rtv", tv)
        self.assertIn("konrad", tv)

        # test for wrong data

        # invalid credentials


        product_data = dict()
        product_data["user"] = dict(username = "invalid", password = "deprofudnis")
        product_data["product"] = dict(
            product_name = "silly walk",
            product_desc = "test",
            price = "1zl",
            category = "rtv"
        )



        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "invalid")
        product_data["product"] = dict(
            product_name = "silly walk",
            product_desc = "test",
            price = "1200pounds",
            category = "rtv"
        )

        # invalid password

        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(403, resp.code)
        self.assertIn("Invalid Credentials", resp.body)

        product_data = dict()
        product_data["user"] = dict(username = "invalid", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "silly walk",
            product_desc = "test",
            price = "1200pounds",
            category = "rtv"
        )

        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(403, resp.code)
        self.assertIn("Invalid Credentials", resp.body)

        #missing fields


        product_data = dict()
        product_data["product"] = dict(
            product_name = "silly walk",
            product_desc = "test",
            price = "1200pounds",
            category = "rtv"
        )

        # no user data

        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(400, resp.code)
        self.assertIn("not parsed properly", resp.body)

        # no product data

        product_data = dict()
        product_data["user"] = dict(username = "invalid", password = "deprofundis")
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(400, resp.code)
        self.assertIn("not parsed properly", resp.body)

        # missing product fields

        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_desc = "test",
            price = "1200pounds",
            category = "rtv"
        )


        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(400, resp.code)


        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "silly walk",
            product_desc = "test",
            category = "rtv"
        )


        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(400, resp.code)

        # not unique product name

        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "test",
            category = "rtv"
        )


        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(400, resp.code)

    def test_getting_product_info(self):
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "wruumm",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        resp = self.fetch("/products")
        self.assertEquals(200, resp.code)

        self.assertIn("wiertarka", resp.body)
        self.assertIn("konrad", resp.body)
        self.assertIn("limit", resp.body)

        q = json.loads(resp.body)

        list_of_products = q["products"]
        metadata = q["_metadata"]

        self.assertEquals(1, len(list_of_products))

        first =list_of_products[list_of_products.keys()[0]]
        self.assertEquals("Other", first["category"])
        self.assertEquals("wiertarka", first["product_name"])
        self.assertEquals("konrad", first["seller"])
        self.assertEquals(10, metadata["limit"])
        self.assertEquals(0, metadata["offset"])


        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "slownik",
            product_desc = "wruumm",
            price = "120zl",
            category = "ksiazki"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)
        resp = self.fetch("/products")
        q = json.loads(resp.body)

        # list_of_products = q["products"]
        # metadata = q["_metadata"]

        # self.assertEquals(2, len(list_of_products))

        # second = list_of_products[list_of_products.keys()[1]]

        # # self.assertEquals("ksiazki", second["category"])
        # self.assertEquals("slownik", second["product_name"])

        # some random error here
        # TODO

    def test_getting_item_info(self):
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "wruumm",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        self.assertEquals(201, resp.code)

        res = self.fetch("/product?id=wiertarka&direct=0", method = "GET")
        self.assertEquals(200, res.code)
        self.assertIn("wiertarka", res.body)
        self.assertIn("konrad", res.body)

        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "kaftan",
            product_desc = "wruumm",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        res = self.fetch("/product?id=kaftan")
        self.assertEquals(200, res.code)
        self.assertIn("kaftan", res.body)

        # test for nonexistent

        resp = self.fetch("/product?id=nonexistent")
        self.assertEquals(404, resp.code)

        # for no product given


        resp = self.fetch("/product?id=nonexistent")
        self.assertEquals(404, resp.code)

        #test getting by uuid

        sel = select([products.c.product_uuid]).where(products.c.product_name == "wiertarka")

        pr_uuid = self.conn.execute(sel).scalar()

        resp = self.fetch("/product?id="+ pr_uuid + "&direct=1")

        self.assertEquals(200, resp.code)
        self.assertIn("wiertarka", resp.body)

        #test for non existent 

        rand = str(uuid.uuid4())

        resp = self.fetch("/product?id="+ rand + "&direct=1")
        self.assertEquals(404, resp.code)


    def test_remote_authentication(self):
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))






    def test_updating_product(self):
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "wruumm",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        data = dict()

        data["user"] = dict(
            username = "konrad",
            password = "deprofundis"
        )
        data["update"] = dict(
            product_name = "wiertarka",
            product_desc = "updated"
        )

        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(201, resp.code)
        self.assertIn("updated", resp.body)
        self.assertIn("wiertarka", resp.body)

        # add another item

        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "pralkosuszarka",
            product_desc = "pierze i suszy",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)
        data = dict()

        data["user"] = dict(
            username = "konrad",
            password = "deprofundis"
        )
        data["update"] = dict(
            product_name = "pralkosuszarka",
            price = "50zl"
        )
        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(201, resp.code)
        self.assertIn("50zl", resp.body)

        sel = select([products.c.price]).where(products.c.product_name == "pralkosuszarka")
        res = self.conn.execute(sel).scalar()
        self.assertEquals("50zl", res)

        sel = select([products.c.product_desc]).where(products.c.product_name == "wiertarka")
        res = self.conn.execute(sel).scalar()
        self.assertEquals("updated", res)

        # test for invalid credentials

        data["user"] = dict(
            username = "konrad",
            password = "niewlasciwy"
        )
        data["update"] = dict(
            product_name = "pralkosuszarka",
            price = "50zl"
        )

        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(401, resp.code)


        data["user"] = dict(
            username = "malgosia",
            password = "malgosia"
        )
        data["update"] = dict(
            product_name = "pralkosuszarka",
            price = "50zl"
        )
        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(401, resp.code)

        # test for no product data given
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis"
        )
        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(400, resp.code)
        data = dict()
        data["update"] = dict(
            product_name = "pralkosuszarka",
            price = "50zl"
        )
        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(400, resp.code)
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis"
        )
        data["update"] = dict(
        )
        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(404, resp.code)


        # test for non existent
        data = dict()

        data["user"] = dict(
            username = "konrad",
            password = "deprofundis"
        )
        data["update"] = dict(
            product_name = "wiertarkopralkosuszarka",
            price = "50zl"
        )
        resp = self.fetch("/product", method = "PUT", body = json.dumps(data))

        self.assertEquals(404, resp.code)

    def test_deleting_product(self):

        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "wruumm",
            category = "All",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        res = self.fetch("/product?id=wiertarka&name=konrad&password=deprofundis", method = "DELETE")

        self.assertEquals(201, res.code)
        self.assertIn("Product deleted", res.body)

        resp = self.fetch("/products")
        self.assertNotIn("wiertarka", resp.body)

        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "zmywarka",
            product_desc = "szuruburu",
            category = "agd",
            price = "1200zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        res =  self.fetch("/products")
        self.assertIn("zmywarka", res.body)

        res = self.fetch("/product?id=wiertarka&name=konrad&password=deprofundis", method = "DELETE")

        self.assertEquals(404, res.code)

        res = self.fetch("/product?id=zmywarka&name=konrad&password=deprofundis", method = "DELETE")
        res =  self.fetch("/products")
        self.assertNotIn("zmywarka", res.body)

        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "zmywarka",
            product_desc = "szuruburu",
            category = "agd",
            price = "1200zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        # test for invalid credentials

        res = self.fetch("/product?id=zmywarka&name=malgosia&password=deprofundis", method = "DELETE")
        self.assertEquals(401, res.code)

        res = self.fetch("/product?id=zmywarka&name=konrad&password=nieprawidlowy", method = "DELETE")
        self.assertEquals(401, res.code)


    def test_buying_products(self):
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "wruumm",
            category = "All",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia"
        )
        data["product"] = dict(
            product_name = "wiertarka",
            # product_uuid = "deprofundis",
            quantity = 20
        )

        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        self.assertEquals(201, resp.code)

        sel = select([bought_products]).where(bought_products.c.user_id == 2)

        res = self.conn.execute(sel).fetchone()
        self.assertIn(20, list(res))

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia"
        )
        data["product"] = dict(
            product_name = "wiertarka",
            # product_uuid = "deprofundis",
            quantity = 15
        )

        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        self.assertEquals(201, resp.code)
        sel = select([bought_products]).where(bought_products.c.user_id == 2)

        res = self.conn.execute(sel).fetchone()
        self.assertIn(35, list(res))

        # test for wrong user
        data = dict()
        data["user"] = dict(
            username = "invalid",
            password = "malgosia"
        )
        data["product"] = dict(
            product_name = "wiertarka",
            # product_uuid = "deprofundis",
            quantity = 15
        )
        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        self.assertEquals(404, resp.code)

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "invalid"
        )
        data["product"] = dict(
            product_name = "wiertarka",
            # product_uuid = "deprofundis",
            quantity = 15
        )
        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        self.assertEquals(403, resp.code)

        # test for invalid data

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia"
        )
        data["product"] = dict(
            quantity = 15
        )
        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        self.assertEquals(404, resp.code)

        data = dict()
        data["user"] = dict(
            password = "malgosia"
        )
        data["product"] = dict(
            product_name = "wiertarka",
            quantity = 15
        )
        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        self.assertEquals(404, resp.code)

        # nonexistent item

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "invalid"
        )
        data["product"] = dict(
            product_name = "suszarka",
            # product_uuid = "deprofundis",
            quantity = 15
        )
        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        self.assertEquals(404, resp.code)

    def test_getting_top_products(self):
        data = dict()
        data["user"] = dict(
            username = "konrad",
            password = "deprofundis",
            email = "exaroth@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))
        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "wiertarka",
            product_desc = "wruumm",
            category = "All",
            price = "120zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        product_data = dict()
        product_data["user"] = dict(username = "konrad", password = "deprofundis")
        product_data["product"] = dict(
            product_name = "suszarka",
            product_desc = "brummm",
            category = "rtv",
            price = "1200zl"
        )
        resp = self.fetch("/products", method = "POST", body = json.dumps(product_data))
        self.assertEquals(201, resp.code)

        resp = self.fetch("/products/top")
        self.assertEquals(200, resp.code)
        self.assertIn("No Products", resp.body)

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia"
        )
        data["product"] = dict(
            product_name = "wiertarka",
            # product_uuid = "deprofundis",
            quantity = 20
        )
        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))

        resp = self.fetch("/products/top")
        self.assertEquals(200, resp.code)
        self.assertNotIn("No Products", resp.body)
        self.assertIn("wiertarka", resp.body)

        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia"
        )
        data["product"] = dict(
            product_name = "suszarka",
            quantity = 2
        )
        resp = self.fetch("/products/buy", method = "POST", body = json.dumps(data))
        resp = self.fetch("/products/top")
        self.assertEquals(200, resp.code)
        self.assertIn("suszarka", resp.body)

        resp = self.fetch("/user/malgosia/bought")
        self.assertEquals(200, resp.code)
        self.assertIn("wiertarka", resp.body)
        self.assertIn("suszarka", resp.body)

        resp = self.fetch("/user/konrad/sold")
        self.assertEquals(200, resp.code)
        self.assertIn("wiertarka", resp.body)
        self.assertIn("suszarka", resp.body)
        resp = self.fetch("/user/malgosia/sold")
        self.assertEquals(404, resp.code)

class TestAuthentication(AsyncHTTPTestCase):
    def get_app(self):
        engine = create_engine("sqlite:///:memory:")
        metadata.bind = engine
        self.conn = engine.connect()
        metadata.create_all()
        return Application(self.conn)

    def tearDown(self):
        metadata.drop_all()

    def test_auth_function(self):
        data = dict()
        data["user"] = dict(
            username = u"konrad",
            password = "deprofundis",
            email = "konrad@gmail.com"
        )

        self.fetch("/users", method = "POST", body = json.dumps(data))
        data = dict()
        data["user"] = dict(
            username = "malgosia",
            password = "malgosia",
            email = "malgosia@gmail.com"
        )
        self.fetch("/users", method = "POST", body = json.dumps(data))

        res = self.fetch("/users")

        res = self.fetch("/auth?username=konrad&password=deprofundis", method = "GET" )

        self.assertEquals(200, res.code)
        self.assertEquals(1, int(res.body))

        res = self.fetch("/auth?username=malgosia&password=malgosia", method = "GET" )

        self.assertEquals(200, res.code)
        self.assertEquals(1, int(res.body))

        res = self.fetch("/auth?username=nonexistent&password=test", method = "GET" )
        self.assertEquals(200, res.code)
        self.assertEquals(0, int(res.body))

        res = self.fetch("/auth?username=konrad&password=test", method = "GET" )
        self.assertEquals(200, res.code)
        self.assertEquals(0, int(res.body))

        res = self.fetch("/auth?username=konrad&password=deprofundis&persist=1", method = "GET" )

if __name__ == "__main__":
    tornado.testing.main()


