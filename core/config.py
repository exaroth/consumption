import os, sys



BASE_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.dirname(BASE_PATH + "..")

DATABASE_PATH = "sqlite:///" + ROOT_PATH + "/test.db"

USER_FIELDS = ("uuid", "username", "password", "email")
CUSTOM_USER_FIELDS = ("password", "email" )

PRODUCT_FIELDS = ("uuid", "product_name", "product_desc" )
CUSTOM_PRODUCT_FIELDS = ("name", "desc")


SECRET_KEY = "super-secret"

DEBUG = True

