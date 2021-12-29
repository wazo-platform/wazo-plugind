# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    contains,
    empty,
    equal_to,
    has_entries,
    has_property,
    is_,
)
from requests import HTTPError
from wazo_test_helpers.hamcrest.raises import raises
from .helpers.base import BaseIntegrationTest

PLUGIN_COUNT = 24


class TestMarket(BaseIntegrationTest):

    asset = 'market'

    def test_get(self):
        assert_that(
            calling(self.get_market).with_args(
                'official', 'admin-ui-conference', token='invalid-token'
            ),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 401))
            ),
        )

        assert_that(
            calling(self.get_market).with_args('foobar', 'foobar'),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 404))
            ),
        )

        result = self.get_market('official', 'admin-ui-conference')
        assert_that(
            result, has_entries('name', 'admin-ui-conference', 'namespace', 'official')
        )

    def test_that_no_filter_returns_all_plugins(self):
        response = self.search()

        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(PLUGIN_COUNT))

    def test_with_a_search_term(self):
        response = self.search('conference')

        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(
            response['items'],
            contains(
                has_entries('name', 'admin-ui-conference', 'namespace', 'official')
            ),
        )

    def test_with_search_and_pagination(self):
        response = self.search(
            'official', limit=5, offset=5, order='name', direction='asc'
        )

        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(16))
        assert_that(
            response['items'],
            contains(
                has_entries('name', 'admin-ui-group'),
                has_entries('name', 'admin-ui-incall'),
                has_entries('name', 'admin-ui-ivr'),
                has_entries('name', 'admin-ui-moh'),
                has_entries('name', 'admin-ui-outcall'),
            ),
        )

    def test_market_installation(self):
        self.uninstall_plugin(
            namespace='markettests', name='foobar', _async=False, ignore_errors=True
        )

        self.install_plugin(
            method='market',
            options={'namespace': 'markettests', 'name': 'foobar'},
            _async=False,
        )

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

    def test_market_installation_with_a_version_field(self):
        self.uninstall_plugin(
            namespace='markettests', name='foobar', _async=False, ignore_errors=True
        )

        self.install_plugin(
            method='market',
            options={'namespace': 'markettests', 'name': 'foobar', 'version': '0.0.1'},
            _async=False,
        )

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

    def test_installed_version_field(self):
        ns, name = 'markettests', 'foobar'

        self.install_plugin(
            method='market', options={'namespace': ns, 'name': name}, _async=False
        )

        response = self.search(name=name)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(
            response['items'],
            contains(
                has_entries('installed_version', '0.0.1', 'namespace', ns, 'name', name)
            ),
        )

        self.uninstall_plugin(ns, name, _async=False)

        response = self.search(name=name)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(
            response['items'],
            contains(
                has_entries('installed_version', None, 'namespace', ns, 'name', name)
            ),
        )

    def test_installed_query_filter(self):
        ns, name = 'markettests', 'foobar'

        self.install_plugin(
            method='market', options={'namespace': ns, 'name': name}, _async=False
        )

        response = self.search(name=name, installed=True)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(
            response['items'], contains(has_entries('namespace', ns, 'name', name))
        )

        response = self.search(name=name, installed=False)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(0))
        assert_that(response['items'], empty())

        self.uninstall_plugin(ns, name, _async=False)

        response = self.search(name=name, installed=False)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(
            response['items'], contains(has_entries('namespace', ns, 'name', name))
        )

        response = self.search(name=name, installed=True)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(0))
        assert_that(response['items'], empty())
