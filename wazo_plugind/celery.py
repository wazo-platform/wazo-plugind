# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
from multiprocessing import Process
from celery import Celery

logger = logging.getLogger(__name__)

worker = None
root_worker = None


class _Worker(object):

    def __init__(self, app, worker_args):
        self._worker_args = ['-d', '-n', self._worker_name] + worker_args
        self.app = app

    def run(self):
        logger.info('starting celery worker')
        self._process = Process(target=self.app.worker_main, kwargs=dict(argv=self._worker_args))
        self._process.start()

    @classmethod
    def from_config(cls, config):
        bus_config = config['celery'][cls._bus_config_section]
        broker_uri = config['celery']['broker']
        pidfile = config['celery'][cls._bus_config_section]['pid_file']
        app = Celery('plugind_tasks', broker=broker_uri)
        app.conf.update(cls._worker_config)
        app.conf.update(config)
        app.conf.update(
            CELERYD_LOG_LEVEL='debug' if config['debug'] else config['log_level'],
            CELERY_DEFAULT_EXCHANGE=bus_config['exchange_name'],
            CELERY_DEFAULT_QUEUE=bus_config['queue_name'],
            CELERY_DEFAULT_ROUTING_KEY=bus_config['routing_key'],
            CELERYD_HIJACK_ROOT_LOGGER=False,
        )
        return cls(app, ['--pidfile', pidfile])


class RootWorker(_Worker):

    _bus_config_section = 'priviledged'
    _worker_config = dict(
        CELERY_ACCEPT_CONTENT=['json'],
        CELERY_IGNORE_RESULT=False,
        CELERY_TASK_SERIALIZER='json',
        CELERY_RESULT_SERIALIZER='json',
        CELERY_RESULT_BACKEND='amqp',
        CELERY_IMPORTS=('wazo_plugind.root_tasks',),
    )
    _worker_name = 'plugind_root_worker@%h'

    def run(self):
        c_force_root = os.environ.get('C_FORCE_ROOT', 'false')
        os.environ['C_FORCE_ROOT'] = 'true'
        super().run()
        os.environ['C_FORCE_ROOT'] = c_force_root


class Worker(_Worker):

    _bus_config_section = 'unpriviledged'
    _worker_config = dict(
        CELERY_ACCEPT_CONTENT=['json', 'pickle'],
        CELERY_IGNORE_RESULT=True,
        CELERY_IMPORTS=('wazo_plugind.tasks',),
    )
    _worker_name = 'plugind_worker@%h'
