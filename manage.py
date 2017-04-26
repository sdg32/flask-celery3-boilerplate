# -*- coding: utf-8 -*-

from flask_migrate import Migrate
from flask_migrate import MigrateCommand
from flask_script import Manager
from flask_script import Shell

from app import app
from app import db

manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    from app.schedule.models import CrontabSchedule
    from app.schedule.models import IntervalSchedule
    from app.schedule.models import ScheduleTask
    from app.schedule.models import ScheduleMeta
    from app.schedule.models import ScheduleInfo

    return dict(app=app, db=db, CrontabSchedule=CrontabSchedule,
                IntervalSchedule=IntervalSchedule, ScheduleTask=ScheduleTask,
                ScheduleMeta=ScheduleMeta, ScheduleInfo=ScheduleInfo)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()
