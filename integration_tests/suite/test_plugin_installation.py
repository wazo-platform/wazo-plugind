# Copyright 2017-2022 The Wazo Authors  (see the AUTHORS file)
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
    has_length,
)
from requests import HTTPError
from unittest.mock import ANY
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises
from wazo_test_helpers.hamcrest.uuid_ import uuid_
from .helpers.base import autoremove, BaseIntegrationTest


class TestPluginList(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_that_an_unauthorized_token_return_401(self):
        plugind_unauthorized = self.make_plugind(token='expired')
        assert_that(
            calling(plugind_unauthorized.plugins.list),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 401))
            ),
        )

    def test_that_installed_plugins_are_listed(self):
        response = self.plugind.plugins.list()

        assert_that(response['total'], equal_to(0))
        assert_that(response['items'], empty())

        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        result = self.plugind.plugins.list()

        assert_that(result['total'], equal_to(1))
        assert_that(
            result['items'],
            contains(has_entries(namespace='plugindtests', name='foobar')),
        )


class TestPluginDependencies(BaseIntegrationTest):

    asset = 'dependency'

    @autoremove('dependency', 'one')
    @autoremove('dependency', 'two')
    @autoremove('dependency', 'three')
    @autoremove('dependency', 'four')
    def test_that_dependencies_are_installed(self):
        self.install_plugin(
            url=None,
            method='market',
            options={'namespace': 'dependency', 'name': 'one'},
            _async=False,
        )

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
        self.install_plugin(
            url=None,
            method='market',
            options={'namespace': 'dependency', 'name': 'two'},
            _async=False,
        )

        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        self.install_plugin(
            url=None,
            method='market',
            options={'namespace': 'dependency', 'name': 'one'},
            _async=False,
        )

        def assert_received(bus_accumulator):
            events = bus_accumulator.accumulate(with_headers=True)
            completed = [
                event
                for event in events
                if event['message']['data']['status'] == 'completed'
            ]
            assert_that(completed, has_length(4))

        until.assert_(assert_received, events, tries=5)

    @autoremove('dependency', 'three')
    def test_given_dependency_error_when_install_then_error(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = self.install_plugin(
            url=None,
            method='market',
            options={'namespace': 'dependencynotfound', 'name': 'one'},
            _async=False,
        )

        one_is_installed = self._is_installed('wazo-plugind-one-dependencynotfound')
        three_is_installed = self._is_installed('wazo-plugind-three-dependency')

        assert_that(one_is_installed, equal_to(False), 'one should not be installed')
        assert_that(three_is_installed, equal_to(True), 'three should be installed')

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        headers=has_entries(
                            name='plugin_install_progress',
                        ),
                        message=has_entries(
                            data=has_entries(
                                uuid=result['uuid'],
                                status='error',
                                errors=has_entries(
                                    details=has_entries(
                                        install_options=has_entries(
                                            url='file:///data/git/dependencynotfound-one',
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    has_entries(
                        headers=has_entries(
                            name='plugin_install_progress',
                        ),
                        message=has_entries(
                            data=has_entries(
                                uuid=ANY,
                                status='error',
                                errors=has_entries(
                                    details=has_entries(
                                        install_options=has_entries(
                                            name='not-found',
                                            namespace='dependency',
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=5)


class TestPluginInstallation(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_when_it_works(self):
        self.uninstall_plugin(
            namespace='plugindtests', name='foobar', _async=False, ignore_errors=True
        )

        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = self.install_plugin(url='file:///data/git/repo', method='git')

        assert_that(result, has_entries(uuid=uuid_()))

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='building')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='packaging')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='updating')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='installing')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='completed')
                        ),
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=10)

        build_success_exists = self.exists_in_container('/tmp/results/build_success')
        package_success_exists = self.exists_in_container(
            '/tmp/results/package_success'
        )
        install_success_exists = self.exists_in_container(
            '/tmp/results/install_success'
        )

        assert_that(
            build_success_exists, is_(True), 'build_success was not created or copied'
        )
        assert_that(
            install_success_exists, is_(True), 'install_success was not created'
        )
        assert_that(
            package_success_exists, is_(True), 'package_success was not created'
        )

    def test_get_plugin(self):
        namespace, name = 'plugindtests', 'foobar'

        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        result = self.plugind.plugins.get(namespace, name)

        assert_that(
            result,
            has_entries('namespace', namespace, 'name', name, 'version', '0.0.1'),
        )

        assert_that(
            calling(self.plugind.plugins.get).with_args(namespace, 'not-foobar'),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 404))
            ),
        )

        plugind_unauthorized = self.make_plugind(token='invalid-token')
        assert_that(
            calling(plugind_unauthorized.plugins.get).with_args(
                namespace, 'not-foobar'
            ),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 401))
            ),
        )

    def test_plugin_debian_dependency(self):
        dependency = 'tig'
        if self._is_installed(dependency):
            self.docker_exec(['apt-get' '-y', 'remove', dependency])

        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        assert_that(self._is_installed(dependency), equal_to(True))

    def test_install_from_git_branch(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = self.install_plugin(
            url='file:///data/git/repo', method='git', options=dict(ref='v2')
        )

        assert_that(result, has_entries(uuid=uuid_()))

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='building')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='packaging')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='updating')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='installing')
                        ),
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='completed')
                        ),
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=10)

        package_success_exists = self.exists_in_container(
            '/tmp/results/package_success_2'
        )

        assert_that(
            package_success_exists, is_(True), 'package_success was not created'
        )

    def test_with_a_postrm(self):
        self.install_plugin(url='file:///data/git/postrm', method='git', _async=False)

        self.uninstall_plugin(namespace='plugindtests', name='postrm', _async=False)

        postinst_success_exists = self.exists_in_container(
            '/tmp/results/postinst_success'
        )
        postrm_success_exists = self.exists_in_container('/tmp/results/postrm_success')

        assert_that(postinst_success_exists, equal_to(False))
        assert_that(postrm_success_exists, equal_to(True))

    def test_that_installing_twice_completes_without_reinstalling(self):
        self.install_plugin(url='file:///data/git/repo2', method='git', _async=False)

        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = self.install_plugin(url='file:///data/git/repo2', method='git')
        assert_that(result, has_entries(uuid=uuid_()))

        def assert_received_in_order(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                contains(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='validating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='completed'),
                        )
                    ),
                ),
            )

        until.assert_(assert_received_in_order, events, tries=5)

    def test_that_installing_twice_with_reinstall_option_reinstalls(self):
        self.install_plugin(url='file:///data/git/repo2', method='git', _async=False)

        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = self.install_plugin(
            url='file:///data/git/repo2', method='git', reinstall=True
        )
        assert_that(result, has_entries(uuid=uuid_()))

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='building'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='packaging'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='updating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='installing'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='completed'),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=10)

    def test_when_uninstall_works(self):
        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        events = self.bus.accumulator(headers={'name': 'plugin_uninstall_progress'})

        result = self.uninstall_plugin(namespace='plugindtests', name='foobar')

        assert_that(result, has_entries(uuid=uuid_()))

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='removing'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='completed'),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=10)

        build_success_exists = self.exists_in_container('/tmp/results/build_success')
        package_success_exists = self.exists_in_container(
            '/tmp/results/package_success'
        )

        assert_that(build_success_exists, is_(False), 'build_success was not removed')
        assert_that(
            package_success_exists, is_(False), 'package_success was not removed'
        )

    def test_that_plugin_build_directory_is_removed_after_an_install(self):
        self.install_plugin(url='file:///data/git/repo', method='git', _async=False)

        directory_is_empty = self.directory_is_empty_in_container(
            '/var/lib/wazo-plugind/tmp'
        )

        assert_that(directory_is_empty, is_(True))

    def test_when_with_an_unknown_plugin_format_version(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = self.install_plugin(url='file:///data/git/futureversion', method='git')

        assert_that(result, has_entries(uuid=uuid_()))

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='validating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='error'),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=5)

    def test_that_uninstalling_an_uninstalled_plugin_returns_404(self):
        assert_that(
            calling(self.uninstall_plugin).with_args(
                namespace='plugindtests', name='uninstalled'
            ),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 404))
            ),
        )

    def test_with_a_max_version_too_small(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})

        result = self.install_plugin(url='/data/git/max_version', method='git')

        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'max_wazo_version': {
                    'message': ANY,
                    'constraint': ANY,
                    'constraint_id': 'range',
                }
            },
        }

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='validating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                uuid=result['uuid'],
                                status='error',
                                errors=errors,
                            ),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=5)

    def test_with_a_min_version_too_high(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})
        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'min_wazo_version': {
                    'message': ANY,
                    'constraint': ANY,
                    'constraint_id': 'range',
                }
            },
        }

        result = self.install_plugin(url='/data/git/min_version', method='git')

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='validating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                uuid=result['uuid'],
                                status='error',
                                errors=errors,
                            ),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=5)

    def test_with_invalid_namespace(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})
        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'namespace': {
                    'message': ANY,
                    'constraint': '^[a-z0-9]+$',
                    'constraint_id': 'regex',
                }
            },
        }

        result = self.install_plugin(url='/data/git/fail_namespace', method='git')

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='validating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                uuid=result['uuid'],
                                status='error',
                                errors=errors,
                            ),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=5)

    def test_with_invalid_name(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})
        errors = {
            'error_id': 'validation-error',
            'message': 'Validation error',
            'resource': 'plugins',
            'details': {
                'name': {
                    'message': ANY,
                    'constraint': '^[a-z0-9-]+$',
                    'constraint_id': 'regex',
                }
            },
        }

        result = self.install_plugin(url='/data/git/fail_name', method='git')

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                has_items(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='validating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                uuid=result['uuid'],
                                status='error',
                                errors=errors,
                            ),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=5)

    def test_that_an_unauthorized_token_return_401(self):
        assert_that(
            calling(self.install_plugin).with_args(
                url='/data/git/repo', method='git', token='expired'
            ),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 401))
            ),
        )

    def test_that_an_unauthorized_token_return_401_when_uninstall(self):
        assert_that(
            calling(self.uninstall_plugin).with_args(
                namespace='plugindtests', name='foobar', token='expired'
            ),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 401))
            ),
        )

    def test_that_an_unknown_download_method_returns_400(self):
        assert_that(
            calling(self.install_plugin).with_args(url='/data/git/repo', method='svn'),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 400))
            ),
        )

    def test_that_an_out_of_date_debian_cache_does_not_break_package_install(self):
        self.install_plugin(
            url='file:///data/git/add_wazo_source_list', method='git', _async=False
        )
        self.install_plugin(
            url='file:///data/git/add_pubkeys', method='git', _async=False
        )

        ssh_key_installed = self.exists_in_container('/root/.ssh/authorized_keys2')

        assert_that(ssh_key_installed, equal_to(True))

    def test_a_plugin_with_a_failing_build_step(self):
        events = self.bus.accumulator(headers={'name': 'plugin_install_progress'})
        errors = {
            'error_id': 'install-error',
            'message': 'Installation error',
            'resource': 'plugins',
            'details': {'step': 'building'},
        }

        result = self.install_plugin(url='file:///data/git/failing_build', method='git')

        def assert_received(bus_accumulator):
            assert_that(
                bus_accumulator.accumulate(with_headers=True),
                contains(
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='starting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='downloading'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='extracting'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='validating'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                uuid=result['uuid'], status='installing dependencies'
                            ),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(uuid=result['uuid'], status='building'),
                        )
                    ),
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                uuid=result['uuid'],
                                status='error',
                                errors=errors,
                            ),
                        )
                    ),
                ),
            )

        until.assert_(assert_received, events, tries=5)
