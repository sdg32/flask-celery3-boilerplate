# -*- coding: utf-8 -*-

from celery import current_app as celery_app
from celery import schedules
from celery.beat import ScheduleEntry
from celery.beat import Scheduler
from celery.utils.log import get_logger

from app import db
from .models import CrontabSchedule
from .models import IntervalSchedule
from .models import ScheduleTask
from .models import ScheduleInfo

logger = get_logger(__name__)


DEFAULT_MAX_INTERVAL = 5


class ModelEntry(ScheduleEntry):

    model_schedules = (
        (schedules.crontab, CrontabSchedule, 'crontab'),
        (schedules.schedule, IntervalSchedule, 'interval')
    )

    def __init__(self, model, app=None):
        super().__init__(
            name=model.name,
            task=model.task,
            last_run_at=model.meta.last_run_at,
            total_run_count=model.meta.total_run_count,
            schedule=model.schedule,
            args=model.args,
            kwargs=model.kwargs,
            options={
                'queue': model.queue,
                'exchange': model.exchange,
                'routing_key': model.routing_key,
                'expires': model.expires_at
            },

            app=app or celery_app._get_current_object()
        )

        self.model = model

    def __next__(self):
        self.model.meta.last_run_at = self._default_now()
        self.model.meta.total_run_count += 1
        db.session.add(self.model.meta)
        db.session.commit()

        return self.__class__(model=self.model, app=self.app)

    def is_due(self):
        if not self.model.is_enabled:
            return False, 5.0

        return super().is_due()

    @classmethod
    def from_orig_entry(cls, name, app=None, **entry):
        instance = ScheduleTask.query.filter_by(name=name).first()
        if not instance:
            instance = ScheduleTask(name=name)

        for k, v in cls._unpack_entry_fields(**entry).items():
            setattr(instance, k, v)
        instance.is_enabled = True
        db.session.add(instance)
        db.session.commit()

        return cls(model=instance, app=app)

    @classmethod
    def to_model_schedule(cls, schedule):
        for schedule_type, model_type, model_field in cls.model_schedules:
            schedule = schedules.maybe_schedule(schedule)
            if isinstance(schedule, schedule_type):
                model_schedule = model_type.from_schedule(schedule)
                return model_schedule, model_field

        raise ValueError(
            'Cannot convert schedule type {0!r} to model'.format(schedule)
        )

    @classmethod
    def _unpack_entry_fields(cls, schedule, args=None, kwargs=None,
                             relative=None, options=None, **entry):
        def _unpack_entry_options(queue=None, exchange=None, routing_key=None,
                                  **kwargs):
            return {
                'queue': queue,
                'exchange': exchange,
                'routing_key': routing_key
            }

        model_schedule, model_field = cls.to_model_schedule(schedule)
        entry.update(
            {
                model_field: model_schedule
            },
            args=args or [],
            kwargs=kwargs or {},
            **_unpack_entry_options(**options or {})
        )
        return entry


class DatabaseScheduler(Scheduler):

    _schedule = None
    _initial_read = False
    _last_timestamp = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Rewrite `max_interval` to a shorter time
        self.max_interval = kwargs.get('max_interval') or DEFAULT_MAX_INTERVAL

    def setup_schedule(self):
        self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.CELERYBEAT_SCHEDULE)

    def install_default_entries(self, data):
        entries = {}
        if self.app.conf.CELERY_TASK_RESULT_EXPIRES:
            # Add backend clean up
            entries.setdefault(
                'celery.backend_cleanup', {
                    'task': 'celery.backend_cleanup',
                    'schedule': schedules.crontab('0', '4', '*')
                }
            )

        self.update_from_dict(entries)

    def update_from_dict(self, dict_):
        _schedules = dict([
            (name, ModelEntry.from_orig_entry(name, app=self.app, **entry))
            for name, entry in dict_.items()
        ])
        return self.schedule.update(_schedules)

    def all_as_schedule(self):
        logger.info('DatabaseScheduler: fetching database schedules...')
        return dict([
                        (x.name, ModelEntry(x, app=self.app))
                        for x in ScheduleTask.get_available_tasks()
                        ])

    @property
    def is_schedule_changed(self):
        change_at = ScheduleInfo.get_last_change_at()
        ts = self._last_timestamp or change_at

        if change_at and change_at > ts:
            self._last_timestamp = change_at
            return True

        self._last_timestamp = change_at
        return False

    @property
    def schedule(self):
        update = False
        if not self._initial_read:
            logger.info('DatabaseScheduler: initial read')
            update = True
            self._initial_read = True
        elif self.is_schedule_changed:
            logger.info('DatabaseScheduler: schedule changed')
            update = True

        if update:
            self._schedule = self.all_as_schedule()

        return self._schedule
