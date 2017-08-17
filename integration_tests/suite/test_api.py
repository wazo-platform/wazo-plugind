# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import time
from hamcrest import assert_that, has_entry, has_entries, has_items
from xivo_test_helpers import until
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

    def get_client(self, token=VALID_TOKEN, version=None):
        port = self.service_port(9503)
        client_args = {
            'port': port,
            'token': token,
            'verify_certificate': False,
            'timeout': 20,
        }
        if version:
            client_args['version'] = version
        return Client('localhost', **client_args)

    def get_market(self, namespace, name, **kwargs):
        client = self.get_client(**kwargs)
        return client.market.get(namespace, name)

    def get_plugin(self, namespace, name, **kwargs):
        client = self.get_client(**kwargs)
        return client.plugins.get(namespace, name)

    def install_plugin(self, url=None, method=None, **kwargs):
        is_async = kwargs.pop('_async', True)
        options = kwargs.pop('options', None)
        client = self.get_client(**kwargs)

        result = client.plugins.install(url, method, options)
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

    def search(self, *args, **kwargs):
        client = self.get_client()
        return client.market.list(*args, **kwargs)

    def list_file_in_container_dir(self, dir_path):
        output = self.docker_exec(['ls', dir_path])
        for current_filename in output.split('\n'):
            if not current_filename:
                continue
            yield current_filename

    def directory_is_empty_in_container(self, path):
        for filename in self.list_file_in_container_dir(path):
            return False
        return True

    def exists_in_container(self, path):
        directory, filename = os.path.split(path)
        for current_filename in self.list_file_in_container_dir(directory):
            if current_filename == filename:
                return True
        return False

    def _is_installed(self, search):
        installed_packages = self.docker_exec(['dpkg-query', '-W', '-f=${binary:Package}\n'])
        for debian_package in installed_packages.split('\n'):
            if debian_package == search:
                return True
        return False

    def assert_status_received(self, msg_accumulator, operation, uuid, status, exclusive=False, **kwargs):
        event_name = 'plugin_{}_progress'.format(operation)

        def match():
            expected_data = ['status', status, 'uuid', uuid]
            for key, value in kwargs.iteritems():
                expected_data.append(key)
                expected_data.append(value)

            received_msg = msg_accumulator.accumulate()
            assert_that(received_msg, has_items(
                has_entry('name', event_name),
                has_entry('data', has_entries(*expected_data))))

        def exclusive_match():
            while True:
                first = msg_accumulator.pop()

                # skip unrelated messages
                if first.get('data', {}).get('uuid') != uuid:
                    continue
                if first.get('name') != event_name:
                    continue

                if first['data']['status'] == status:
                    return

                msg_accumulator.push_back(first)
                self.fail('{} is not at the top of the accumulator, received {}'.format(status, first))

        aux = exclusive_match if exclusive else match
        until.assert_(aux, tries=120, interval=0.5,
                      message='The bus message should have been received: {}'.format(status))
