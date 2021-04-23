# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import time

from functools import wraps
from requests import HTTPError
from hamcrest import assert_that, has_entry, has_entries, has_items
from xivo_test_helpers import until
from xivo_test_helpers.bus import BusClient
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from wazo_plugind_client import Client

VALID_TOKEN = 'valid-token-multitenant'
TOKEN_SUB_TENANT = 'valid-token-sub-tenant'


def autoremove(namespace, plugin):
    def decorator(f):
        @wraps(f)
        def decorated(self, *args, **kwargs):
            try:
                result = f(self, *args, **kwargs)
            finally:
                try:
                    self.uninstall_plugin(namespace, plugin)
                except HTTPError:
                    pass
            return result

        return decorated

    return decorator


class BaseIntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../..', 'assets')
    )
    service = 'plugind'
    bus_config = dict(user='guest', password='guest', host='127.0.0.1')

    def setUp(self):
        self.msg_accumulator = self.new_message_accumulator('plugin.#')

    def tearDown(self):
        self.docker_exec(['rm', '-rf', '/tmp/results'], service_name='plugind')

    def docker_exec(self, *args, **kwargs):
        return super().docker_exec(*args, **kwargs).decode('utf-8')

    def get_client(self, token=VALID_TOKEN, version=None):
        port = self.service_port(9503)
        client_args = {
            'port': port,
            'prefix': None,
            'https': False,
            'token': token,
            'timeout': 20,
        }
        if version:
            client_args['version'] = version
        return Client('127.0.0.1', **client_args)

    def get_market(self, namespace, name, **kwargs):
        client = self.get_client(**kwargs)
        return client.market.get(namespace, name)

    def get_plugin(self, namespace, name, **kwargs):
        client = self.get_client(**kwargs)
        return client.plugins.get(namespace, name)

    def install_plugin(self, url=None, method=None, **kwargs):
        reinstall = kwargs.pop('reinstall', None)
        is_async = kwargs.pop('_async', True)
        options = kwargs.pop('options', None)
        client = self.get_client(**kwargs)

        result = client.plugins.install(url, method, options, reinstall=reinstall)
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
        ignore_errors = kwargs.pop('ignore_errors', False)
        is_async = kwargs.pop('_async', True)
        client = self.get_client(*kwargs)

        try:
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
        except HTTPError:
            if not ignore_errors:
                raise

    def new_message_accumulator(self, routing_key):
        port = self.service_port(5672, service_name='rabbitmq')
        bus = BusClient.from_connection_fields(port=port, **self.bus_config)
        return bus.accumulator(routing_key)

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

    def _is_installed(self, search, version=None):
        installed_packages = self.docker_exec(
            ['dpkg-query', '-W', '-f=${binary:Package} ${Version}\n']
        )
        for line in installed_packages.split('\n'):
            if not line:
                continue

            debian_package, installed_version = line.split(' ', 1)
            if debian_package == search:
                if not version:
                    return True
                return version == installed_version
        return False

    def assert_status_received(
        self, msg_accumulator, operation, uuid, status, exclusive=False, **kwargs
    ):
        event_name = 'plugin_{}_progress'.format(operation)

        def match():
            expected_data = ['status', status, 'uuid', uuid]
            for key, value in kwargs.items():
                expected_data.append(key)
                expected_data.append(value)

            received_msg = msg_accumulator.accumulate()
            assert_that(
                received_msg,
                has_items(
                    has_entry('name', event_name),
                    has_entry('data', has_entries(*expected_data)),
                ),
            )

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
                self.fail(
                    '{} is not at the top of the accumulator, received {}'.format(
                        status, first
                    )
                )

        aux = exclusive_match if exclusive else match
        until.assert_(
            aux,
            tries=120,
            interval=0.5,
            message='The bus message should have been received: {}'.format(status),
        )
