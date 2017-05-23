# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
from multiprocessing import Process
from celery import Celery

logger = logging.getLogger(__name__)

worker = None
root_worker = None


class RootWorker(object):

    _bus_config_section = 'priviledged'
    _worker_config = dict(
        CELERY_ACCEPT_CONTENT=['json'],
        CELERYD_HIJACK_ROOT_LOGGER=False,
        CELERY_IGNORE_RESULT=False,
        CELERY_TASK_SERIALIZER='json',
        CELERY_RESULT_SERIALIZER='json',
        CELERY_RESULT_BACKEND='amqp',
        CELERY_IMPORTS=('wazo_plugind.root_tasks',),
    )

    def __init__(self, app):
        logger.debug('New RootWorker created with app: %s', app)
        self._worker_args = ['-d', '-n', 'plugind_root_worker@%h']
        self.app = app

    def run(self):
        logger.info('starting celery root worker: %s', self.app)
        c_force_root = os.environ.get('C_FORCE_ROOT', 'false')
        os.environ['C_FORCE_ROOT'] = 'true'
        self._process = Process(target=self.app.worker_main, kwargs=dict(argv=self._worker_args))
        self._process.start()
        os.environ['C_FORCE_ROOT'] = c_force_root

    @classmethod
    def from_config(cls, config):
        bus_config = config['celery'][cls._bus_config_section]
        broker_uri = config['celery']['broker']
        app = Celery('plugind_tasks', broker=broker_uri)
        app.conf.update(cls._worker_config)
        app.conf.update(config)
        app.conf.update(
            CELERYD_LOG_LEVEL='debug' if config['debug'] else config['log_level'],
            CELERY_DEFAULT_EXCHANGE=bus_config['exchange_name'],
            CELERY_DEFAULT_QUEUE=bus_config['queue_name'],
            CELERY_DEFAULT_ROUTING_KEY=bus_config['routing_key'],
        )
        return cls(app)


class Worker(object):

    _bus_config_section = 'unpriviledged'
    _worker_config = dict(
        CELERY_ACCEPT_CONTENT=['json', 'pickle'],
        CELERYD_HIJACK_ROOT_LOGGER=False,
        CELERY_IGNORE_RESULT=False,
        CELERY_RESULT_SERIALIZER='pickle',
        CELERY_RESULT_BACKEND='amqp',
        CELERY_IMPORTS=('wazo_plugind.tasks',),
    )

    def __init__(self, app):
        self.app = app
        self._worker_args = ['-d', '-n', 'plugind_worker@%h']

    def run(self):
        logger.info('starting celery worker')
        self._process = Process(target=self.app.worker_main, kwargs=dict(argv=self._worker_args))
        self._process.start()

    @classmethod
    def from_config(cls, config):
        broker_uri = config['celery']['broker']
        bus_config = config['celery'][cls._bus_config_section]
        app = Celery('plugind_tasks', broker=broker_uri)
        app.conf.update(cls._worker_config)
        app.conf.update(config)
        app.conf.update(
            CELERYD_LOG_LEVEL='debug' if config['debug'] else config['log_level'],
            CELERY_DEFAULT_EXCHANGE=bus_config['exchange_name'],
            CELERY_DEFAULT_QUEUE=bus_config['queue_name'],
            CELERY_DEFAULT_ROUTING_KEY=bus_config['routing_key'],
        )
        return cls(app)
