import os, sys


BASE_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.dirname(BASE_PATH + "..")

# define sqlalchemy database path here
DATABASE_PATH = "sqlite:///" + ROOT_PATH + "/test.db"

#all the user fields
USER_FIELDS = ("uuid", "username", "password", "email", "joined")
# fields that can be changed by the user
CUSTOM_USER_FIELDS = ("password", "email" )
# fields that should be hidden from unauthorized access
SECURE_USER_FIELDS = ("password", "email", "uuid")

#all product fields
PRODUCT_FIELDS = ("uuid", "product_name", "product_desc", "category" )
# product fields that can be customized
CUSTOM_PRODUCT_FIELDS = ("product_name", "product_desc", "category")


# unique secret key used for encrypting passwords
SECRET_KEY = "super-secret"

DEBUG = True

