from sqlalchemy import create_engine
from sqlalchemy import Table, Column, String, Unicode, Integer, MetaData, ForeignKey, UniqueConstraint, ForeignKeyConstraint, DateTime
from config import *


engine = create_engine(DATABASE_PATH)
metadata = MetaData()



users = Table("users", metadata,
              Column("user_id", Integer, primary_key = True),
              Column("user_uuid", String, nullable = False),
              Column("username", String(40), nullable = False),
              Column("password", String(40)),
              Column("email", String(40), nullable = False),
              Column("joined", String),
              UniqueConstraint("user_uuid", "username", "email")
             )

bought_products = Table("bought_products", metadata, 
                        Column("bought_id", Integer, primary_key = True),
                        Column("quantity", Integer, nullable = False),
                        Column("user_id", Integer, ForeignKey("users.user_id", ondelete="CASCADE")),
                        Column("product_id", Integer, ForeignKey("products.product_id", ondelete="CASCADE")),

                        # option for postgresql db
                        #  ForeignKeyConstraint(
                        #      ["user_id", "product_id"],
                        #      ["users.user_id", "products.product_id"],
                        #      on_update="CASCADE", on_delete="CASCADE"
                        #  )
                       )

products = Table("products", metadata,
                 Column("product_id", Integer, primary_key = True),
                 Column("product_uuid", String, nullable = False),
                 Column("product_name", String(40), nullable = False),
                 Column("product_desc", String),
                 Column("category", String(40)),
                 Column("price", String),
                 # Column("seller", ForeignKey("users.user_id")),
                 Column("seller", String(30)),
                 UniqueConstraint("product_uuid", "product_name")
                )

"""
add event for properly handling cascading in sqlite 

"""

def on_connect(conn, record):
    conn.execute("pragma foreign_keys=ON")


from sqlalchemy import event 
event.listen(engine, "connect", on_connect)

