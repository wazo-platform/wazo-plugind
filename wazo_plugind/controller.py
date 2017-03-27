# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import signal
import sys
from threading import Lock
from contextlib import contextmanager
from cherrypy import wsgiserver
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from xivo import http_helpers
from xivo.consul_helpers import Registerer
from wazo_plugind import http

logger = logging.getLogger(__name__)
registerer_lock = Lock()


def _signal_handler(signum, frame):
    logger.info('SIGTERM received, terminating')
    sys.exit(0)


def _register(registerer, self_check_fn):
    self_check_fn()
    with registerer_lock:
        registerer.register()


@contextmanager
def service_discovery(name, uuid, consul_config, service_discovery_config, self_check_fn):
    if not uuid:
        logger.info('XIVO_UUID is undefined. service discovery disabled')
        try:
            yield
        finally:
            return

    registerer = Registerer(name, uuid, consul_config, service_discovery_config)
    _register(registerer, self_check_fn)
    try:
        yield
    finally:
        with registerer_lock:
            if registerer.registered():
                registerer.deregister()


class Controller(object):

    def __init__(self, config):
        listen_addr = config['rest_api']['https']['listen']
        listen_port = config['rest_api']['https']['port']
        self._cors_config = config['rest_api']['cors']
        ssl_cert_file = config['rest_api']['https']['certificate']
        ssl_key_file = config['rest_api']['https']['private_key']
        self._consul_config = config['consul']
        self._service_discovery_config = config['service_discovery']
        self._xivo_uuid = config.get('uuid')
        # TODO find how its configured using the builtin ssl adapter
        # ssl_ciphers = config['rest_api']['https']['ciphers']
        bind_addr = (listen_addr, listen_port)
        flask_app = self._new_flask_app(config)
        Adapter = wsgiserver.get_ssl_adapter_class('builtin')
        adapter = Adapter(ssl_cert_file, ssl_key_file)
        wsgiserver.CherryPyWSGIServer.ssl_adapter = adapter
        wsgi_app = wsgiserver.WSGIPathInfoDispatcher({'/': flask_app})
        self._server = wsgiserver.CherryPyWSGIServer(bind_addr=bind_addr, wsgi_app=wsgi_app)
        for route in http_helpers.list_routes(flask_app):
            logger.debug(route)

    def run(self):
        logger.debug('starting http server')
        signal.signal(signal.SIGTERM, _signal_handler)
        with service_discovery('wazo-plugind', self._xivo_uuid,
                               self._consul_config, self._service_discovery_config,
                               lambda: True):
            try:
                self._server.start()
            except KeyboardInterrupt:
                logger.info("Ctrl-C received, terminating")
            finally:
                self._server.stop()

    def _new_flask_app(self, config):
        app = Flask('wazo_plugind')
        app.config.update(config)
        api = Api(app, prefix='/0.1')
        http.Api.add_resource(api)
        http.Config.add_resource(api, config)
        if self._cors_config.get('enabled'):
            CORS(app, **self._cors_config)
        return app
