# -*- coding: utf-8 -*-

from threading import Thread

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from celery import Celery

from config import Config


app = Flask(__name__, instance_relative_config=True)
app.config.from_object(Config)
app.config.setdefault('BROKER_URL', 'redis://localhost:6379/0')
app.config.setdefault('CELERYBEAT_SCHEDULER',
                      'app.schedule.schedulers.DatabaseScheduler')
app.config.setdefault('CELERY_RESULT_BACKEND',
                      'app.schedule.backends.DatabaseBackend')
app.config.setdefault('CELERY_SEND_EVENTS', True)
app.config.setdefault('CELERY_SEND_TASK_SENT_EVENT', True)

db = SQLAlchemy(app)
celery = Celery('proj')
celery.config_from_object(app.config)
celery_state = celery.events.State()
_celery_thread = None


def _run_celery_background():
    global _celery_thread
    global celery_state

    def _monitor():
        with celery.connection() as cnn:
            recv = celery.events.Receiver(cnn,
                                          handlers={'*': celery_state.event})
            recv.capture(limit=None, timeout=None, wakeup=True)

    _celery_thread = Thread(target=_monitor)
    _celery_thread.daemon = True
    _celery_thread.start()


if not _celery_thread:
    _run_celery_background()

from . import schedule
