# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from hamcrest import assert_that, has_entries, has_items, any_of
from functools import wraps
from requests import HTTPError
from wazo_test_helpers import until
from wazo_test_helpers.bus import BusClient
from wazo_test_helpers.auth import AuthClient, MockUserToken, MockCredentials
from wazo_test_helpers.asset_launching_test_case import (
    AssetLaunchingTestCase,
    NoSuchPort,
    NoSuchService,
    WrongClient,
)
from wazo_plugind_client import Client as PlugindClient
from .wait_strategy import EverythingOkWaitStrategy

MAIN_TENANT = '00000000-0000-4000-8000-000000000201'
MAIN_USER_UUID = '00000000-0000-4000-8000-000000000301'
TOKEN = '00000000-0000-4000-8000-000000000101'

SUB_TENANT = '00000000-0000-4000-8000-000000000202'
SUB_USER_UUID = '00000000-0000-4000-8000-000000000302'
TOKEN_SUB_TENANT = '00000000-0000-4000-8000-000000000102'

WAZO_UUID = '00000000-0000-4000-8000-00003eb8004d'


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

    wait_strategy = EverythingOkWaitStrategy()

    @classmethod
    def make_plugind(cls, token=TOKEN):
        try:
            port = cls.service_port(9503, 'plugind')
        except (NoSuchService, NoSuchPort):
            return WrongClient('plugind')
        return PlugindClient(
            '127.0.0.1',
            port=port,
            prefix=None,
            https=False,
            token=token,
            timeout=20,
        )

    @classmethod
    def configure_token(cls):
        if isinstance(cls.auth, WrongClient):
            return

        cls.auth.set_token(
            MockUserToken(
                TOKEN,
                MAIN_USER_UUID,
                WAZO_UUID,
                {'tenant_uuid': MAIN_TENANT, 'uuid': MAIN_USER_UUID},
            )
        )
        cls.auth.set_token(
            MockUserToken(
                TOKEN_SUB_TENANT,
                SUB_USER_UUID,
                WAZO_UUID,
                {'tenant_uuid': SUB_TENANT, 'uuid': SUB_USER_UUID},
            )
        )
        cls.auth.set_tenants(
            {
                'uuid': MAIN_TENANT,
                'name': 'plugind-tests-master',
                'parent_uuid': MAIN_TENANT,
            },
            {
                'uuid': SUB_TENANT,
                'name': 'plugind-tests-users',
                'parent_uuid': MAIN_TENANT,
            },
        )

    @classmethod
    def configure_service_token(cls):
        if isinstance(cls.auth, WrongClient):
            return

        credentials = MockCredentials('plugind-service', 'plugind-password')
        cls.auth.set_valid_credentials(credentials, TOKEN)

    @classmethod
    def make_auth(cls):
        try:
            port = cls.service_port(9497, 'auth')
        except (NoSuchService, NoSuchPort):
            return WrongClient('auth')
        return AuthClient('127.0.0.1', port=port)

    def tearDown(self):
        self.docker_exec(['rm', '-rf', '/tmp/results'], service_name='plugind')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = cls.make_auth()
        cls.configure_token()
        cls.configure_service_token()
        cls.plugind = cls.make_plugind()
        cls.bus = cls.setup_bus()
        cls.wait_strategy.wait(cls)

    @classmethod
    def setup_bus(cls):
        try:
            port = cls.service_port(5672, 'rabbitmq')
        except NoSuchPort:
            raise

        bus = BusClient.from_connection_fields(port=port, **cls.bus_config)
        return bus

    def docker_exec(self, *args, **kwargs):
        return super().docker_exec(*args, **kwargs).decode('utf-8')

    @classmethod
    def reset_clients(cls):
        cls.plugind = cls.make_plugind()
        cls.auth = cls.make_auth()
        cls.bus = cls.setup_bus()

    def install_plugin(self, url=None, method=None, version=None, **kwargs):
        reinstall = kwargs.pop('reinstall', None)
        is_async = kwargs.pop('_async', True)
        options = kwargs.pop('options', None)
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        plugind = self.make_plugind(**kwargs)
        result = plugind.plugins.install(url, method, options, reinstall=reinstall)
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

        until.assert_(assert_received, events, timeout=60)
        return result

    def uninstall_plugin(self, namespace, name, **kwargs):
        ignore_errors = kwargs.pop('ignore_errors', False)
        is_async = kwargs.pop('_async', True)
        events = self.bus.accumulator(headers={'name': 'plugin_uninstall_progress'})
        plugind = self.make_plugind(**kwargs)

        try:
            result = plugind.plugins.uninstall(namespace, name)
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
