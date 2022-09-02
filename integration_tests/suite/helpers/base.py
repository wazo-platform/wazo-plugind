# Copyright 2017-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from kombu import Exchange
from hamcrest import assert_that, has_entries, has_items, any_of
from functools import wraps
from requests import HTTPError
from wazo_test_helpers import until
from wazo_test_helpers.bus import BusClient
from wazo_test_helpers.asset_launching_test_case import (
    AssetLaunchingTestCase,
    NoSuchPort,
)
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
    bus_config = dict(
        user='guest',
        password='guest',
        host='127.0.0.1',
        exchange_name='wazo-headers',
        exchange_type='headers',
    )

    def tearDown(self):
        self.docker_exec(['rm', '-rf', '/tmp/results'], service_name='plugind')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bus = cls.setup_bus()

    @classmethod
    def setup_bus(cls):
        try:
            port = cls.service_port(5672, 'rabbitmq')
        except NoSuchPort:
            raise

        upstream = Exchange('xivo', 'topic')
        bus = BusClient.from_connection_fields(port=port, **cls.bus_config)
        bus.downstream_exchange_declare('wazo-headers', 'headers', upstream)
        return bus

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
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = client.plugins.install(url, method, options, reinstall=reinstall)
        if is_async:
            return result

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                status=any_of('completed', 'error'),
                                uuid=result['uuid'],
                            )
                        ),
                        headers=has_entries(name='plugin_install_progress'),
                    )
                ),
            )

        until.assert_(assert_received, events, timeout=30)
        return result

    def list_plugins(self, **kwargs):
        client = self.get_client(**kwargs)
        return client.plugins.list()

    def uninstall_plugin(self, namespace, name, **kwargs):
        ignore_errors = kwargs.pop('ignore_errors', False)
        is_async = kwargs.pop('_async', True)
        client = self.get_client(*kwargs)
        events = self.bus.accumulator(headers={'name': 'plugin_uninstall_progress'})

        try:
            result = client.plugins.uninstall(namespace, name)
            if is_async:
                return result
        except HTTPError:
            if not ignore_errors:
                raise
            return

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                status=any_of('completed', 'error'),
                                uuid=result['uuid'],
                            )
                        ),
                        headers=has_entries(name='plugin_uninstall_progress'),
                    )
                ),
            )

        until.assert_(assert_received, events, timeout=30)
        return result

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
