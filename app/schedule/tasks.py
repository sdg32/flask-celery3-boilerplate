# -*- coding: utf-8 -*-

from datetime import datetime
import time

from celery import shared_task


@shared_task
def test_sleep_1():
    time.sleep(1)
    print(datetime.now())


@shared_task
def test_sleep_3():
    time.sleep(3)
    print(datetime.now())
