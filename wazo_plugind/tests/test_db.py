# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, contains, equal_to
from mock import Mock, patch

from ..config import _DEFAULT_CONFIG
from ..db import MarketDB, MarketProxy, Plugin


class TestPlugin(TestCase):

    def test_is_installed_no_arguments(self):
        namespace, name = 'foo', 'bar'

        plugin = Plugin(_DEFAULT_CONFIG, name, namespace)
        plugin._metadata = {'namespace': namespace, 'name': name}

        assert_that(plugin.is_installed(), equal_to(True))

    def test_is_installed_not_installed(self):
        namespace, name = 'foo', 'bar'

        plugin = Plugin(_DEFAULT_CONFIG, name, namespace)

        with patch.object(plugin, 'metadata', return_value=None):
            assert_that(plugin.is_installed(), equal_to(False))

        with patch.object(plugin, 'metadata', side_effect=IOError):
            assert_that(plugin.is_installed(), equal_to(False))

    def test_is_installed_with_version(self):
        namespace, name, version = 'foo', 'bar', '0.0.1'

        plugin = Plugin(_DEFAULT_CONFIG, name, namespace)

        with patch.object(plugin, 'metadata', return_value={'version': '0.0.2'}):
            assert_that(plugin.is_installed(version), equal_to(False))

        with patch.object(plugin, 'metadata', return_value={'version': version}):
            assert_that(plugin.is_installed(version), equal_to(True))


class TestMarketDB(TestCase):

    def setUp(self):
        self.content = [
            {'name': 'a', 'namespace': 'c'},
            {'name': 'b'},
            {'namespace': 'a'},
        ]
        self.market_proxy = Mock(MarketProxy)
        self.market_proxy.get_content.return_value = self.content

    def test_sort_direction(self):
        a, b, c = self.content

        db = MarketDB(self.market_proxy)

        results = db.list_(order='name', direction='asc')
        assert_that(results, contains(a, b, c))

        results = db.list_(order='name', direction='desc')
        assert_that(results, contains(c, b, a))

    def test_sort_order(self):
        a, b, c = self.content

        db = MarketDB(self.market_proxy)

        results = db.list_(order='name', direction='asc')
        assert_that(results, contains(a, b, c))

        results = db.list_(order='namespace', direction='asc')
        assert_that(results, contains(c, a, b))
