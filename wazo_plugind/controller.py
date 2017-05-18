# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import signal
import sys
from threading import Thread
from functools import partial
from celery import Celery
from cherrypy import wsgiserver
from xivo import http_helpers
from xivo.consul_helpers import ServiceCatalogRegistration
from wazo_plugind import http, bus, service
from .service_discovery import self_check

logger = logging.getLogger(__name__)


def _signal_handler(signum, frame):
    logger.info('SIGTERM received, terminating')
    sys.exit(0)


class CeleryWorker(object):

    _worker_config = dict(
        CELERY_ACCEPT_CONTENT=['json'],
        CELERYD_HIJACK_ROOT_LOGGER=False,
    )

    def __init__(self, celery):
        self._celery = celery

    def run(self):
        logger.info('starting celery worker')
        worker_args = sys.argv[1:] + ['-n', 'plugind_worker@%h']
        self._thread = Thread(target=self._celery.worker_main, kwargs=dict(argv=worker_args))
        self._thread.daemon = True
        self._thread.start()

    @classmethod
    def from_config(cls, config):
        broker_uri = config['celery']['broker']
        celery = Celery('plugind_tasks', broker=broker_uri)
        celery.conf.update(cls._worker_config)
        celery.conf.update(config)
        celery.conf.update(
            CELERYD_LOG_LEVEL='debug' if config['debug'] else config['log_level'],
            CELERY_DEFAULT_EXCHANGE=config['celery']['exchange_name'],
        )
        return cls(celery)


class Controller(object):

    def __init__(self, config, worker):
        self._xivo_uuid = config.get('uuid')
        self._listen_addr = config['rest_api']['https']['listen']
        self._listen_port = config['rest_api']['https']['port']
        self._cors_config = config['rest_api']['cors']
        ssl_cert_file = config['rest_api']['https']['certificate']
        ssl_key_file = config['rest_api']['https']['private_key']
        self._consul_config = config['consul']
        self._service_discovery_config = config['service_discovery']
        self._bus_config = config['bus']
        # TODO find how its configured using the builtin ssl adapter
        # ssl_ciphers = config['rest_api']['https']['ciphers']
        bind_addr = (self._listen_addr, self._listen_port)
        self._publisher = bus.StatusPublisher.from_config(config)
        plugin_service = service.PluginService(config, worker, self._publisher)
        flask_app = http.new_app(config, plugin_service=plugin_service)
        Adapter = wsgiserver.get_ssl_adapter_class('builtin')
        adapter = Adapter(ssl_cert_file, ssl_key_file)
        wsgiserver.CherryPyWSGIServer.ssl_adapter = adapter
        wsgi_app = wsgiserver.WSGIPathInfoDispatcher({'/': flask_app})
        self._server = wsgiserver.CherryPyWSGIServer(bind_addr=bind_addr, wsgi_app=wsgi_app)
        for route in http_helpers.list_routes(flask_app):
            logger.debug(route)
        self._worker = worker
        self._celery_worker = CeleryWorker.from_config(config)

    def run(self):
        logger.debug('starting http server')
        signal.signal(signal.SIGTERM, _signal_handler)
        publisher_thread = Thread(target=self._publisher.run)
        publisher_thread.start()
        self._celery_worker.run()
        with ServiceCatalogRegistration(
                'wazo-plugind',
                self._xivo_uuid,
                self._consul_config,
                self._service_discovery_config,
                self._bus_config,
                partial(self_check, self._listen_port),
        ):
            try:
                self._server.start()
            except (KeyboardInterrupt, SystemExit):
                logger.info('Main process stopping')
            finally:
                self._server.stop()
        self._worker.stop()
        self._publisher.stop()
        publisher_thread.join()
