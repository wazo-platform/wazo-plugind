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
    is_,
)
from requests import HTTPError
from unittest import skip
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers.hamcrest.uuid_ import uuid_
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

        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        result = self.list_plugins()

        assert_that(result['total'], equal_to(1))
        assert_that(result['items'], contains(has_entries(namespace='plugindtests',
                                                          name='foobar')))


class TestPluginInstallation(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_when_it_works(self):
        dependency = 'tig'
        assert_that(self._is_installed(dependency), equal_to(False),
                    'Test precondition, {} should not be installed'.format(dependency))

        result = self.install_plugin(url='file:///data/git/repo', method='git')

        assert_that(result, has_entries(uuid=uuid_()))

        statuses = ['starting', 'downloading', 'extracting', 'building',
                    'packaging', 'updating', 'installing', 'completed']
        for status in statuses:
            self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], status)

        build_success_exists = self.exists_in_container('/tmp/results/build_success')
        package_success_exists = self.exists_in_container('/tmp/results/package_success')
        install_success_exists = self.exists_in_container('/tmp/results/install_success')

        assert_that(build_success_exists, is_(True), 'build_success was not created or copied')
        assert_that(install_success_exists, is_(True), 'install_success was not created')
        assert_that(package_success_exists, is_(True), 'package_success was not created')
        assert_that(self._is_installed(dependency), equal_to(True))

    def test_with_a_postrm(self):
        self.install_plugin(url='file:///data/git/postrm', method='git', _async=False)

        self.uninstall_plugin(namespace='plugindtests', name='postrm', _async=False)

        postinst_success_exists = self.exists_in_container('/tmp/results/postinst_success')
        postrm_success_exists = self.exists_in_container('/tmp/results/postrm_success')

        assert_that(postinst_success_exists, equal_to(False))
        assert_that(postrm_success_exists, equal_to(True))

    def test_that_installing_twice_completes_with_reinstalling(self):
        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        result = self.install_plugin(url='file:///data/git/repo', method='git')

        assert_that(result, has_entries(uuid=uuid_()))
        statuses = ['starting', 'downloading', 'extracting', 'completed']
        for status in statuses:
            self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], status, exclusive=True)

    def test_when_uninstall_works(self):
        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        result = self.uninstall_plugin(namespace='plugindtests', name='foobar')

        assert_that(result, has_entries(uuid=uuid_()))

        statuses = ['starting', 'removing', 'completed']
        for status in statuses:
            self.assert_status_received(self.msg_accumulator, 'uninstall', result['uuid'], status)

        build_success_exists = self.exists_in_container('/tmp/results/build_success')
        package_success_exists = self.exists_in_container('/tmp/results/package_success')

        assert_that(build_success_exists, is_(False), 'build_success was not removed')
        assert_that(package_success_exists, is_(False), 'package_success was not removed')

    def test_that_uninstalling_an_uninstalled_plugin_returns_404(self):
        assert_that(calling(self.uninstall_plugin).with_args(namespace='plugindtests',
                                                             name='uninstalled'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 404))))

    @skip('to be enabled when async errors are implemented')
    def test_with_invalid_namespace(self):
        assert_that(calling(self.install_plugin).with_args(url='/data/git/fail_namespace', method='git'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 500))))

    @skip('to be enabled when async errors are implemented')
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

    def test_that_an_unknown_download_method_returns_400(self):
        assert_that(calling(self.install_plugin).with_args(url='/data/git/repo', method='svn'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 400))))

    def test_that_an_out_of_date_debian_cache_does_not_break_package_install(self):
        self.install_plugin(url='file:///data/git/add_wazo_source_list', method='git', _async=False)
        self.install_plugin(url='file:///data/git/add_pubkeys', method='git', _async=False)

        ssh_key_installed = self.exists_in_container('/root/.ssh/authorized_keys2')

        assert_that(ssh_key_installed, equal_to(True))

    def exists_in_container(self, path):
        directory, filename = os.path.split(path)
        output = self.docker_exec(['ls', directory])
        for current_filename in output.split('\n'):
            if current_filename == filename:
                return True
        return False

    def _is_installed(self, search):
        installed_packages = self.docker_exec(['dpkg-query', '-W', '-f=${binary:Package}\n'])
        for debian_package in installed_packages.split('\n'):
            if debian_package == search:
                return True
        return False

    def assert_status_received(self, msg_accumulator, operation, uuid, status, exclusive=False):
        event_name = 'plugin_{}_progress'.format(operation)

        def match():
            assert_that(msg_accumulator.accumulate(), has_item(all_of(
                has_entry('name', event_name),
                has_entry('data', has_entries('status', status, 'uuid', uuid)))))

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
