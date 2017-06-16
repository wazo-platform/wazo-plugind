# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import time
from xivo_test_helpers.bus import BusClient
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from wazo_plugind_client import Client

VALID_TOKEN = 'valid-token'


class BaseIntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    service = 'plugind'
    bus_config = dict(username='guest', password='guest', host='localhost')

    def setUp(self):
        self.msg_accumulator = self.new_message_accumulator('plugin.#')

    def tearDown(self):
        self.docker_exec(['rm', '-rf', '/tmp/results'], service_name='plugind')

    def get_client(self, token=VALID_TOKEN):
        port = self.service_port(9503)
        return Client('localhost', port=port, token=token, verify_certificate=False, timeout=20)

    def install_plugin(self, url, method, **kwargs):
        is_async = kwargs.pop('_async', True)
        client = self.get_client(**kwargs)
        result = client.plugins.install(url, method)
        if is_async:
            return result

        while True:
            messages = self.msg_accumulator.accumulate()
            for message in messages:
                if message['data']['uuid'] != result['uuid']:
                    continue
                if message['data']['status'] in ['completed', 'error']:
                    return result
            time.sleep(0.25)

    def list_plugins(self, **kwargs):
        client = self.get_client(**kwargs)
        return client.plugins.list()

    def uninstall_plugin(self, namespace, name, **kwargs):
        is_async = kwargs.pop('_async', True)
        client = self.get_client(*kwargs)
        result = client.plugins.uninstall(namespace, name)
        if is_async:
            return result

        while True:
            messages = self.msg_accumulator.accumulate()
            for message in messages:
                if message['data']['uuid'] != result['uuid']:
                    continue
                if message['data']['status'] in ['completed', 'error']:
                    return result
            time.sleep(0.25)

    def new_message_accumulator(self, routing_key):
        port = self.service_port(5672, service_name='rabbitmq')
        bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(port=port, **self.bus_config)
        return BusClient(bus_url).accumulator(routing_key)
