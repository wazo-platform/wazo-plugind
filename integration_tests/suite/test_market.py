# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that, contains, equal_to, has_entries
from .test_api import BaseIntegrationTest

PLUGIN_COUNT = 23


class TestMarketList(BaseIntegrationTest):

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
        assert_that(response['filtered'], equal_to(17))
        assert_that(response['items'], contains(
            has_entries('name', 'admin-ui-group'),
            has_entries('name', 'admin-ui-incall'),
            has_entries('name', 'admin-ui-ivr'),
            has_entries('name', 'admin-ui-moh'),
            has_entries('name', 'admin-ui-outcall'),
        ))
