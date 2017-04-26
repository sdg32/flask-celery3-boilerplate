# -*- coding: utf-8 -*-

from datetime import datetime
from datetime import timedelta
import json

from celery import current_app as celery_app
from celery import schedules
from sqlalchemy import event

from app import db


class CrontabSchedule(db.Model):

    __tablename__ = 'crontab'

    id = db.Column(db.Integer, primary_key=True)
    minute = db.Column(db.String(50), default='*')
    hour = db.Column(db.String(50), default='*')
    day_of_week = db.Column(db.String(50), default='*')
    day_of_month = db.Column(db.String(50), default='*')
    month_of_year = db.Column(db.String(50), default='*')

    tasks = db.relationship('ScheduleTask', backref='crontab', lazy='dynamic')

    @property
    def schedule(self):
        return schedules.crontab(
            minute=self.minute,
            hour=self.hour,
            day_of_week=self.day_of_week,
            day_of_month=self.day_of_month,
            month_of_year=self.month_of_year
        )

    @classmethod
    def from_schedule(cls, schedule):
        data = dict([
            (x, getattr(schedule, '_orig_{0}'.format(x)))
            for x in (
                'minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year'
            )
        ])
        instance = cls.query.filter(*[
            getattr(cls, k) == v for k, v in data.items()
        ]).first()
        if not instance:
            instance = cls(**data)
            db.session.add(instance)
            db.session.commit()
        return instance

    def __repr__(self):
        return self.schedule


class IntervalSchedule(db.Model):

    __tablename__ = 'interval'

    id = db.Column(db.Integer, primary_key=True)
    every = db.Column(db.Integer, default=1)
    period = db.Column(db.String(20))

    tasks = db.relationship('ScheduleTask', backref='interval', lazy='dynamic')

    @property
    def schedule(self):
        return schedules.schedule(timedelta(**{self.period: self.every}))

    @classmethod
    def from_schedule(cls, schedule):
        every = max(schedule.run_every.total_seconds(), 0)
        instance = cls.query.filter_by(every=every, period='seconds')
        if not instance:
            instance = cls(every=every, period='seconds')
            db.session.add(instance)
            db.session.commit()
        return instance

    def __repr__(self):
        return self.schedule


class ScheduleTask(db.Model):

    __tablename__ = 'schedule_task'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    task = db.Column(db.String(100))
    task_args = db.Column(db.Text, default='[]')
    task_kwargs = db.Column(db.Text, default='{}')
    crontab_id = db.Column(db.Integer, db.ForeignKey('crontab.id'))
    interval_id = db.Column(db.Integer, db.ForeignKey('interval.id'))
    is_enabled = db.Column(db.Boolean, default=True)
    queue = db.Column(db.String(200))
    exchange = db.Column(db.String(200))
    routing_key = db.Column(db.String(200))
    expires_at = db.Column(db.DateTime)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    modified_at = db.Column(db.DateTime, default=datetime.now)

    @property
    def meta(self):
        instance = ScheduleMeta.query.get(self.id)
        if not instance:
            instance = ScheduleMeta(parent_id=self.id)
            db.session.add(instance)
            db.session.commit()
        return instance

    @property
    def args(self):
        return json.loads(self.task_args)

    @args.setter
    def args(self, data):
        self.task_args = json.dumps(data)

    @property
    def kwargs(self):
        return json.loads(self.task_kwargs)

    @kwargs.setter
    def kwargs(self, data):
        self.task_kwargs = json.dumps(data)

    @property
    def schedule(self):
        if self.crontab:
            return self.crontab.schedule
        if self.interval:
            return self.interval.schedule

    @classmethod
    def get_available_tasks(cls):
        db.session.expire_all()
        return (
            x for x in cls.query.filter_by(is_enabled=True).all()
            if x.task in celery_app.tasks
        )

    def __repr__(self):
        return '<ScheduleTask {0}>'.format(self.name)


class ScheduleMeta(db.Model):

    __tablename__ = 'schedule_meta'

    parent_id = db.Column(db.Integer, db.ForeignKey('schedule_task.id'),
                          primary_key=True)
    last_run_at = db.Column(db.DateTime)
    total_run_count = db.Column(db.Integer, default=0)

    parent = db.relationship('ScheduleTask')


class ScheduleInfo(db.Model):

    __tablename__ = 'schedule_info'

    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    last_changed_at = db.Column(db.DateTime, default=datetime.now)

    @classmethod
    def get_last_change_at(cls):
        instance = cls.query.get(1)
        if not instance:
            instance = cls(id=1)
            db.session.add(instance)
            db.session.commit()

        return instance.last_changed_at or datetime.now()


class TaskResult(db.Model):

    __tablename__ = 'task_result'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(50))
    task = db.Column(db.String(100))
    received_at = db.Column(db.DateTime)
    done_at = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    result = db.Column(db.Text)
    traceback = db.Column(db.Text)
    worker = db.Column(db.String(100))
    meta = db.Column(db.Text)


@event.listens_for(CrontabSchedule, 'after_insert')
@event.listens_for(CrontabSchedule, 'after_update')
@event.listens_for(IntervalSchedule, 'after_insert')
@event.listens_for(IntervalSchedule, 'after_update')
@event.listens_for(ScheduleTask, 'after_insert')
@event.listens_for(ScheduleTask, 'after_update')
def update_schedule_info(mapper, connection, target):
    table = ScheduleInfo.__table__
    connection.execute(
        table.update()
        .where(table.c.id == 1)
        .values(last_changed_at=datetime.now())
    )
