# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import threading
import time
from contextlib import contextmanager
from http import client
from xivo.consul_helpers import Registerer, RegistererError

logger = logging.getLogger(__name__)


def self_check(port):
    conn = client.HTTPSConnection('localhost', port)
    try:
        conn.request('GET', '/0.1/config')
    except (client.HTTPException, ConnectionRefusedError):
        return False
    response = conn.getresponse()
    return response.status == 200


class ServiceDiscoveryManager(object):

    _NAME = 'wazo-plugind'

    def __init__(self, config):
        self._is_enabled = config['service_discovery']['enabled']
        if not self._is_enabled:
            logger.info('service discovery is disabled')
            return

        self._xivo_uuid = config.get('uuid')
        if not self._xivo_uuid:
            logger.info('disabling service discovery XIVO_UUID not available')
            self._is_enabled = False
            return

        self._registerer = Registerer(self._NAME,
                                      self._xivo_uuid,
                                      config['consul'],
                                      config['service_discovery'])

        self._should_stop = threading.Event()
        self._registerer_lock = threading.Lock()
        self._check = lambda: True
        self._registerer_thread = None
        self._retry_interval = config['service_discovery']['retry_interval']

    @contextmanager
    def registration(self, self_check_fn):
        logger.info('registration starting')
        self._check = self_check_fn
        if not self._is_enabled:
            return self._registration_disabled()
        else:
            return self._registration_enabled()

    def _deregister(self):
        with self._registerer_lock:
            self._registerer.deregister()

    def _register_loop(self):
        while True:
            if self._should_stop.is_set():
                return
            if self._check():
                logger.info('self check success, registering')
                break
            time.sleep(self._retry_interval)

        while True:
            if self._should_stop.is_set():
                return
            with self._registerer_lock:
                try:
                    self._registerer.register()
                    logger.info('registration completed')
                    break
                except RegistererError:
                    time.sleep(self._retry_interval)

    def _registration_disabled(self):
        try:
            yield
        finally:
            return

    def _registration_enabled(self):
        self._should_stop.clear()
        self._registerer_thread = threading.Thread(target=self._register_loop)
        self._registerer_thread.daemon = True
        self._registerer_thread.start()
        try:
            yield
        finally:
            self._stop_loop()
            self._deregister()

    def _stop_loop(self):
        if not self._should_stop.is_set():
            self._should_stop.set()

        if self._registerer_thread and self._registerer_thread.is_alive():
            self._registerer_thread.join()
