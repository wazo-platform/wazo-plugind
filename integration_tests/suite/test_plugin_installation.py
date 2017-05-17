# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
from hamcrest import (
    all_of,
    assert_that,
    calling,
    contains,
    equal_to,
    empty,
    has_entry,
    has_entries,
    has_item,
    has_property,
    not_,
)
from requests import HTTPError
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers.hamcrest.uuid_ import uuid_
from xivo_test_helpers.bus import BusClient
from xivo_test_helpers import until
from .test_api import BaseIntegrationTest


class TestPluginList(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_that_an_unauthorized_token_return_401(self):
        assert_that(calling(self.list_plugins).with_args(token='expired'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 401))))

    def test_that_installed_plugins_are_listed(self):
        response = self.list_plugins()

        assert_that(response['total'], equal_to(0))
        assert_that(response['items'], empty())

        self.install_plugin(url='file:///data/git/repo', method='git')

        result = self.list_plugins()

        assert_that(result['total'], equal_to(1))
        assert_that(result['items'], contains(has_entries(namespace='plugindtests',
                                                          name='foobar')))


class TestPluginInstallation(BaseIntegrationTest):

    asset = 'plugind_only'

    def setUp(self):
        self.bus_config = dict(username='guest', password='guest', host='localhost')

    def test_when_it_works(self):
        dependency = 'tig'
        assert_that(self._is_installed(dependency), equal_to(False),
                    'Test precondition, {} should not be installed'.format(dependency))

        msg_accumulator = self.new_message_accumulator('plugin.install.#')

        result = self.install_plugin(url='/data/git/repo', method='git')

        build_success_exists = self.exists_in_asset('results/build_success')
        package_success_exists = self.exists_in_asset('results/package_success')
        install_success_exists = self.exists_in_asset('results/install_success')

        assert_that(result, has_entries(uuid=uuid_()))

        statuses = ['starting', 'downloading', 'extracting', 'building',
                    'packaging', 'installing', 'completed']
        for status in statuses:
            self.assert_status_received(msg_accumulator, result['uuid'], status)
        assert_that(build_success_exists, 'build_success was not created or copied')
        assert_that(install_success_exists, 'install_success was not created')
        assert_that(package_success_exists, 'package_success was not created')
        assert_that(self._is_installed(dependency), equal_to(True))

    def test_when_uninstall_works(self):
        self.install_plugin(url='/data/git/repo', method='git')

        result = self.uninstall_plugin(namespace='plugindtests', name='foobar')

        build_success_exists = self.exists_in_asset('results/build_success')
        package_success_exists = self.exists_in_asset('results/package_success')
        install_success_exists = self.exists_in_asset('results/install_success')

        assert_that(result, has_entries(uuid=uuid_()))
        assert_that(not_(build_success_exists), 'build_success was not removed')
        assert_that(not_(install_success_exists), 'install_success was not removed')
        assert_that(not_(package_success_exists), 'package_success was not removed')

    def test_that_uninstalling_an_uninstalled_plugin_returns_404(self):
        assert_that(calling(self.uninstall_plugin).with_args(namespace='plugindtests',
                                                             name='foobar'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 404))))

    def test_with_invalid_namespace(self):
        assert_that(calling(self.install_plugin).with_args(url='/data/git/fail_namespace', method='git'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 500))))

    def test_with_invalid_name(self):
        assert_that(calling(self.install_plugin).with_args(url='/data/git/fail_name', method='git'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 500))))

    def test_that_an_unauthorized_token_return_401(self):
        assert_that(calling(self.install_plugin).with_args(url='/data/git/repo', method='git', token='expired'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 401))))

    def test_that_an_unauthorized_token_return_401_when_uninstall(self):
        assert_that(calling(self.uninstall_plugin).with_args(namespace='plugindtests',
                                                             name='foobar',
                                                             token='expired'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 401))))

    def test_that_an_unknown_download_method_returns_501(self):
        assert_that(calling(self.install_plugin).with_args(url='/data/git/repo', method='svn'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 501))))

    def exists_in_asset(self, path):
        complete_path = self.path_in_asset(path)
        return os.path.exists(complete_path)

    def new_message_accumulator(self, routing_key):
        port = self.service_port(5672, service_name='rabbitmq')
        bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(port=port, **self.bus_config)
        return BusClient(bus_url).accumulator(routing_key)

    def path_in_asset(self, path):
        return os.path.sep.join([self.assets_root, self.asset, path])

    def _is_installed(self, search):
        installed_packages = self.docker_exec(['dpkg-query', '-W', '-f=${binary:Package}\n'])
        for debian_package in installed_packages.split('\n'):
            if debian_package == search:
                return True
        return False

    def assert_status_received(self, msg_accumulator, uuid, status):
        def aux():
            assert_that(msg_accumulator.accumulate(), has_item(all_of(
                has_entry('name', 'plugin_install_progress'),
                has_entry('data', has_entries('status', status, 'uuid', uuid)))))

        until.assert_(aux, tries=10, interval=0.25,
                      message='The bus message should have been received')
