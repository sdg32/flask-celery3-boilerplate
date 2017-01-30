# -*- coding: utf-8 -*-

import json
from datetime import datetime

from celery.backends.base import BaseBackend
from celery.backends.database import retry

from app import db
from app import celery_state
from .models import TaskResult


class DatabaseBackend(BaseBackend):

    subpolling_interval = 0.5

    @staticmethod
    @retry
    def _store_result(task_id, result, status, traceback=None, request=None):
        task = celery_state.tasks[task_id]

        instance = TaskResult.query.filter_by(task_id=task_id).first()
        if not instance:
            instance = TaskResult(task_id=task_id)

        instance.task = task.name
        instance.received_at = datetime.fromtimestamp(task.received)
        instance.done_at = datetime.now()
        instance.status = status
        instance.result = result
        instance.traceback = traceback
        instance.worker = task.worker.hostname
        instance.meta = json.dumps(vars(request))

        db.session.add(instance)
        db.session.commit()
