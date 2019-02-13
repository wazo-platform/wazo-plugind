# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    contains,
    equal_to,
    empty,
    has_entries,
    has_items,
    has_property,
    is_,
)
from requests import HTTPError
from mock import ANY
from xivo_test_helpers import until
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers.hamcrest.uuid_ import uuid_
from .test_api import autoremove, BaseIntegrationTest


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


class TestPluginDependencies(BaseIntegrationTest):

    asset = 'dependency'

    @autoremove('dependency', 'one')
    @autoremove('dependency', 'two')
    @autoremove('dependency', 'three')
    @autoremove('dependency', 'four')
    def test_that_dependencies_are_installed(self):
        self.install_plugin(url=None, method='market', options={'namespace': 'dependency',
                                                                'name': 'one'}, _async=False)

        one_is_installed = self._is_installed('wazo-plugind-one-dependency')
        two_is_installed = self._is_installed('wazo-plugind-two-dependency')
        three_is_installed = self._is_installed('wazo-plugind-three-dependency')
        four_is_installed = self._is_installed('wazo-plugind-four-dependency')

        assert_that(one_is_installed, equal_to(True), 'one should be installed')
        assert_that(two_is_installed, equal_to(True), 'two should be installed')
        assert_that(three_is_installed, equal_to(True), 'three should be installed')
        assert_that(four_is_installed, equal_to(True), 'four should be installed')

    @autoremove('dependency', 'one')
    @autoremove('dependency', 'two')
    @autoremove('dependency', 'three')
    @autoremove('dependency', 'four')
    def test_that_a_satisfied_dependency_does_not_block_the_install(self):
        self.install_plugin(url=None, method='market', options={'namespace': 'dependency',
                                                                'name': 'two'}, _async=False)

        self.msg_accumulator.reset()

        self.install_plugin(url=None, method='market', options={'namespace': 'dependency',
                                                                'name': 'one'}, _async=False)

        def bus_received_all_completed():
            received = self.msg_accumulator.accumulate()
            completed = [msg['data']['uuid'] for msg in received if msg['data']['status'] == 'completed']
            nb_completed = len(completed)
            assert_that(nb_completed, equal_to(4))

        until.assert_(bus_received_all_completed, tries=20, interval=0.5)

    @autoremove('dependency', 'three')
    def test_given_dependency_error_when_install_then_error(self):
        result = self.install_plugin(url=None, method='market', options={'namespace': 'dependencynotfound',
                                                                         'name': 'one'}, _async=False)

        one_is_installed = self._is_installed('wazo-plugind-one-dependencynotfound')
        three_is_installed = self._is_installed('wazo-plugind-three-dependency')

        assert_that(one_is_installed, equal_to(False), 'one should not be installed')
        assert_that(three_is_installed, equal_to(True), 'three should be installed')

        def bus_received_two_errors():
            assert_that(self.msg_accumulator.accumulate(), has_items(
                has_entries({
                    'name': 'plugin_install_progress',
                    'data': has_entries({
                        'uuid': result['uuid'],
                        'status': 'error',
                        'errors': has_entries({
                            'details': has_entries({
                                'install_options': has_entries({
                                    'url': 'file:///data/git/dependencynotfound-one',
                                })
                            })
                        })
                    })
                }), has_entries({
                    'name': 'plugin_install_progress',
                    'data': has_entries({
                        'uuid': ANY,
                        'status': 'error',
                        'errors': has_entries({
                            'details': has_entries({
                                'install_options': has_entries({
                                    'name': 'not-found',
                                    'namespace': 'dependency',
                                })
                            })
                        })
                    })
                })
            ))

        until.assert_(bus_received_two_errors, tries=20, interval=0.5)


class TestPluginInstallation(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_when_it_works(self):
        self.uninstall_plugin(namespace='plugindtests', name='foobar', _async=False, ignore_errors=True)

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

    def test_get_plugin(self):
        namespace, name = 'plugindtests', 'foobar'

        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        result = self.get_plugin(namespace, name)

        assert_that(result, has_entries('namespace', namespace,
                                        'name', name,
                                        'version', '0.0.1'))

        assert_that(calling(self.get_plugin).with_args(namespace, 'not-foobar'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 404))))

        assert_that(calling(self.get_plugin).with_args(namespace, 'not-foobar', token='invalid-token'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 401))))

    def test_plugin_debian_dependency(self):
        dependency = 'tig'
        if self._is_installed(dependency):
            self.docker_exec(['apt-get' '-y', 'remove', dependency])

        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        assert_that(self._is_installed(dependency), equal_to(True))

    def test_install_from_git_branch(self):
        msg_accumulator = self.new_message_accumulator('plugin.install.#')

        result = self.install_plugin(url='file:///data/git/repo', method='git', options=dict(ref='v2'))

        assert_that(result, has_entries(uuid=uuid_()))

        statuses = ['starting', 'downloading', 'extracting', 'building',
                    'packaging', 'updating', 'installing', 'completed']
        for status in statuses:
            self.assert_status_received(msg_accumulator, 'install', result['uuid'], status)

        package_success_exists = self.exists_in_container('/tmp/results/package_success_2')

        assert_that(package_success_exists, is_(True), 'package_success was not created')

    def test_with_a_postrm(self):
        self.install_plugin(url='file:///data/git/postrm', method='git', _async=False)

        self.uninstall_plugin(namespace='plugindtests', name='postrm', _async=False)

        postinst_success_exists = self.exists_in_container('/tmp/results/postinst_success')
        postrm_success_exists = self.exists_in_container('/tmp/results/postrm_success')

        assert_that(postinst_success_exists, equal_to(False))
        assert_that(postrm_success_exists, equal_to(True))

    def test_that_installing_twice_completes_without_reinstalling(self):
        self.install_plugin(url='file:///data/git/repo2', method='git', _async=False)

        result = self.install_plugin(url='file:///data/git/repo2', method='git')
        assert_that(result, has_entries(uuid=uuid_()))
        statuses = ['starting', 'downloading', 'extracting', 'validating', 'completed']
        for status in statuses:
            self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], status, exclusive=True)

    def test_that_installing_twice_with_reinstall_option_reinstalls(self):
        self.install_plugin(url='file:///data/git/repo2', method='git', _async=False)

        result = self.install_plugin(url='file:///data/git/repo2', method='git', reinstall=True)
        assert_that(result, has_entries(uuid=uuid_()))
        statuses = ['starting', 'downloading', 'extracting', 'building',
                    'packaging', 'updating', 'installing', 'completed']
        for status in statuses:
            self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], status)

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

    def test_that_plugin_build_directory_is_removed_after_an_install(self):
        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        directory_is_empty = self.directory_is_empty_in_container('/var/lib/wazo-plugind/tmp')

        assert_that(directory_is_empty, is_(True))

    def test_when_with_an_unknown_plugin_format_version(self):
        result = self.install_plugin(url='file:///data/git/futureversion', method='git')

        assert_that(result, has_entries(uuid=uuid_()))
        statuses = ['starting', 'error']
        for status in statuses:
            self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], status)

    def test_that_uninstalling_an_uninstalled_plugin_returns_404(self):
        assert_that(calling(self.uninstall_plugin).with_args(namespace='plugindtests',
                                                             name='uninstalled'),
                    raises(HTTPError).matching(has_property('response', has_property('status_code', 404))))

    def test_with_a_max_version_too_small(self):
        result = self.install_plugin(url='/data/git/max_version', method='git')

        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'max_wazo_version': {
                    'message': ANY,
                    'constraint': ANY,
                    'constraint_id': 'range'}}}
        self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], 'error', errors=errors)

    def test_with_a_min_version_too_high(self):
        result = self.install_plugin(url='/data/git/min_version', method='git')

        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'min_wazo_version': {
                    'message': ANY,
                    'constraint': ANY,
                    'constraint_id': 'range'}}}
        self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], 'error', errors=errors)

    def test_with_invalid_namespace(self):
        result = self.install_plugin(url='/data/git/fail_namespace', method='git')

        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'namespace': {
                    'message': ANY,
                    'constraint': '^[a-z0-9]+$',
                    'constraint_id': 'regex'}}}
        self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], 'error', errors=errors)

    def test_with_invalid_name(self):
        result = self.install_plugin(url='/data/git/fail_name', method='git')

        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'name': {
                    'message': ANY,
                    'constraint': '^[a-z0-9-]+$',
                    'constraint_id': 'regex'}}}
        self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], 'error', errors=errors)

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

    def test_a_plugin_with_a_failing_build_step(self):
        result = self.install_plugin(url='file:///data/git/failing_build', method='git')

        errors = {
            'error_id': 'install-error',
            'message': 'Installation error',
            'resource': 'plugins',
            'details': {
                'step': 'building',
            },
        }

        self.assert_status_received(self.msg_accumulator, 'install', result['uuid'], 'error', errors=errors)
