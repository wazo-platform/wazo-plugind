# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that, contains, empty, equal_to, has_entries, is_
from .test_api import BaseIntegrationTest

PLUGIN_COUNT = 24


class TestMarket(BaseIntegrationTest):

    asset = 'market'

    def test_that_no_filter_returns_all_plugins(self):
        response = self.search()

        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(PLUGIN_COUNT))

    def test_with_a_search_term(self):
        response = self.search('conference')

        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(response['items'], contains(has_entries('name', 'admin-ui-conference',
                                                            'namespace', 'official')))

    def test_with_search_and_pagination(self):
        response = self.search('official', limit=5, offset=5, order='name', direction='asc')

        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(16))
        assert_that(response['items'], contains(
            has_entries('name', 'admin-ui-group'),
            has_entries('name', 'admin-ui-incall'),
            has_entries('name', 'admin-ui-ivr'),
            has_entries('name', 'admin-ui-moh'),
            has_entries('name', 'admin-ui-outcall'),
        ))

    def test_market_installation(self):
        self.install_plugin(method='market', options={'namespace': 'markettests',
                                                      'name': 'foobar'}, _async=False)

        build_success_exists = self.exists_in_container('/tmp/results/build_success')
        package_success_exists = self.exists_in_container('/tmp/results/package_success')
        install_success_exists = self.exists_in_container('/tmp/results/install_success')

        assert_that(build_success_exists, is_(True), 'build_success was not created or copied')
        assert_that(install_success_exists, is_(True), 'install_success was not created')
        assert_that(package_success_exists, is_(True), 'package_success was not created')

    def test_installed_version_field(self):
        ns, name = 'markettests', 'foobar'

        self.install_plugin(method='market', options={'namespace': ns, 'name': name}, _async=False)

        response = self.search(name=name)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(response['items'], contains(
            has_entries('installed_version', '0.0.1',
                        'namespace', ns,
                        'name', name)))

        self.uninstall_plugin(ns, name, _async=False)

        response = self.search(name=name)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(response['items'], contains(
            has_entries('installed_version', None,
                        'namespace', ns,
                        'name', name)))

    def test_installed_query_filter(self):
        ns, name = 'markettests', 'foobar'

        self.install_plugin(method='market', options={'namespace': ns, 'name': name}, _async=False)

        response = self.search(name=name, installed=True)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(response['items'], contains(
            has_entries('namespace', ns,
                        'name', name)))

        response = self.search(name=name, installed=False)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(0))
        assert_that(response['items'], empty())

        self.uninstall_plugin(ns, name, _async=False)

        response = self.search(name=name, installed=False)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(1))
        assert_that(response['items'], contains(
            has_entries('namespace', ns,
                        'name', name)))

        response = self.search(name=name, installed=True)
        assert_that(response['total'], equal_to(PLUGIN_COUNT))
        assert_that(response['filtered'], equal_to(0))
        assert_that(response['items'], empty())
