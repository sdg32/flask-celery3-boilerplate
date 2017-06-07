# -*- coding: utf-8 -*-

import os

base_dir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(
        os.path.join(base_dir, 'db_dev.sqlite3')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False

    # Celery
    BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERYBEAT_SCHEDULER = 'app.schedule.schedulers.DatabaseScheduler'
    CELERY_RESULT_BACKEND = 'app.schedule.backends.DatabaseBackend'
    CELERY_SEND_EVENTS = True
    CELERY_SEND_TASK_SENT_EVENT = True
    CELERY_ACCEPT_CONTENT = os.getenv('CELERY_ACCEPT_CONTENT', ['json'])
    CELERY_TASK_SERIALIZER = os.getenv('CELERY_TASK_SERIALIZER', 'json')
    CELERY_EVENT_SERIALIZER = os.getenv('CELERY_EVENT_SERIALIZER', 'json')

    # Flask
    DEBUG = True
    TESTING = False
