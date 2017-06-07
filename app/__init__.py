# -*- coding: utf-8 -*-

import os
from threading import Thread

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
from celery import signals

from config import Config


app = Flask(__name__, instance_relative_config=True)
app.config.from_object(Config)

db = SQLAlchemy(app)
celery = Celery('proj')
celery.config_from_object(app.config)
celery_state = celery.events.State()


def run_celery_state_monitor():
    """Run celery state monitor."""
    global celery_state

    def monitor():
        with celery.connection() as cnn:
            recv = celery.events.Receiver(cnn,
                                          handlers={'*': celery_state.event})
            recv.capture(limit=None, timeout=None, wakeup=True)

    t = Thread(target=monitor, daemon=True)
    t.start()


run_celery_state_monitor()


@signals.worker_process_init.connect()
def celery_worker_process_init(*args, **kwargs):
    """Run celery state monitor for every worker process."""
    if os.name != 'nt':
        run_celery_state_monitor()


from . import schedule
