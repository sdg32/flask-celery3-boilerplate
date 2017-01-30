# -*- coding: utf-8 -*-

import os

base_dir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(
        os.path.join(base_dir, 'db_dev.sqlite3')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False

    DEBUG = True
    TESTING = False
