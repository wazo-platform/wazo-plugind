# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from http import client
import logging
import signal
import sys
import time
import threading
from contextlib import contextmanager
from cherrypy import wsgiserver
from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from xivo import http_helpers
from xivo.consul_helpers import Registerer, RegistererError
from wazo_plugind import http

logger = logging.getLogger(__name__)
registerer_lock = threading.Lock()
registerer_run = threading.Event()


def _signal_handler(signum, frame):
    logger.info('SIGTERM received, terminating')
    sys.exit(0)


def _self_check(port):
    logger.info('self check...')
    conn = client.HTTPSConnection('localhost', port)
    try:
        conn.request('GET', '/0.1/config')
    except (client.HTTPException, ConnectionRefusedError):
        return False
    response = conn.getresponse()
    return response.status == 200


def _register(registerer, retry_interval, self_check_fn):
    while True:
        if not registerer_run.is_set():
            return

        if self_check_fn():
            break

        time.sleep(retry_interval)

    while True:
        if not registerer_run.is_set():
            return

        with registerer_lock:
            try:
                registerer.register()
                registerer_run.clear()
                break
            except RegistererError:
                time.sleep(retry_interval)


@contextmanager
def service_discovery(name, uuid, consul_config, service_discovery_config, self_check_fn):
    if not uuid:
        logger.info('XIVO_UUID is undefined. service discovery disabled')
        try:
            yield
        finally:
            return

    registerer = Registerer(name, uuid, consul_config, service_discovery_config)
    registerer_run.set()
    registerer_thread = threading.Thread(target=_register,
                                         args=(registerer,
                                               service_discovery_config['retry_interval'],
                                               self_check_fn))
    registerer_thread.daemon = True
    registerer_thread.start()
    try:
        yield
    finally:
        # If not registered get out of the loop
        if registerer_run.is_set():
            registerer_run.clear()

        # If still alive wait until it complete exiting from its loops
        if registerer_thread.is_alive():
            registerer_thread.join()

        with registerer_lock:
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
                               lambda: _self_check(self._service_discovery_config['advertise_port'])):
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
