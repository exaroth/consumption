from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.options import options
import tornado.web

import simplejson as json

import os, sys
import logging
import uuid

from config import *
from models import users, bought_products, products, engine


logging.basicConfig(filename = ROOT_PATH + "/main_logger.log", level = logging.DEBUG )


class Application(tornado.web.Application):

    def __init__(self):

        handlers = []
        settings = {
            "debug": True
        }
        super(Application, self).__init__(handlers, **settings)
        self.conn = engine.connect()


