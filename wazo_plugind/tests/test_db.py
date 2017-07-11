# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, calling, contains, empty, equal_to, raises
from mock import Mock, patch

from ..config import _DEFAULT_CONFIG
from ..db import iin, normalize_caseless, MarketDB, MarketProxy, Plugin
from ..exceptions import InvalidSortParamException


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


class TestIIn(TestCase):

    def test_iin(self):
        truth = [
            ('ç', 'François'),
            ('franc', 'François'),
        ]
        for left, right in truth:
            result = iin(left, right)
            assert_that(result, equal_to(True))

        falsy = [
            ('a', 42),
        ]
        for left, right in falsy:
            result = iin(left, right)
            assert_that(result, equal_to(False))


class TestNormalizeCaseless(TestCase):

    def test_normalize_caseless(self):
        data = [
            ('abc', 'abc'),
            ('pépé', 'pepe'),
            ('PÉPÉ', 'pepe'),
            ('François', 'francois'),
        ]

        for data, expected in data:
            result = normalize_caseless(data)
            assert_that(result, equal_to(expected))


class TestMarketDB(TestCase):

    def setUp(self):
        self.content = [
            {'name': 'a', 'namespace': 'c', 'tags': ['foobar'], 'd': {}, 'version': '0.1.1', 'min_wazo_version': '1'},
            {'name': 'b', 'tags': ['pépé'], 'd': {42: 'bar'}, 'version': '0.2.0', 'min_wazo_version': '3'},
            {'namespace': 'a', 'version': '0.12.0', 'min_wazo_version': '2'},
        ]
        self.market_proxy = Mock(MarketProxy)
        self.market_proxy.get_content.return_value = self.content
        self.db = MarketDB(self.market_proxy)

    def test_list_with_strict_filter(self):
        a, b, c = self.content

        results = self.db.list_(namespace='a')
        assert_that(results, contains(c))

        results = self.db.list_(name='a', namespace='c', version='0.1.1')
        assert_that(results, contains(a))

        results = self.db.list_(name='a', namespace='c', version='0.1')  # Not full match on version
        assert_that(results, empty())

    def test_get(self):
        self.market_proxy.get_content.return_value = a, b, c = [
            {'namespace': 'foo', 'name': 'bar', 'version': '0.1.1'},
            {'namespace': 'foo', 'name': 'bar', 'version': '0.0.1'},
            {'namespace': 'foo', 'name': 'bar', 'version': '0.2.0'},
        ]

        # Latest version
        result = self.db.get('foo', 'bar')
        assert_that(result, equal_to(c))

        # Specified version
        result = self.db.get('foo', 'bar', '0.0.1')
        assert_that(result, equal_to(b))

        # Unknown version
        assert_that(
            calling(self.db.get).with_args('foo', 'bar', '0.0.42'),
            raises(Exception)
        )

        # Unknown name
        assert_that(
            calling(self.db.get).with_args('foo', 'BAZ'),
            raises(Exception)
        )

    def test_search(self):
        a, b, c = self.content

        results = self.db.list_(search='a')
        assert_that(results, contains(a, c))

        results = self.db.list_(search='foo')
        assert_that(results, contains(a))

        results = self.db.list_(search='pe')
        assert_that(results, contains(b))

    def test_sort_direction(self):
        a, b, c = self.content

        results = self.db.list_(order='name', direction='asc')
        assert_that(results, contains(a, b, c))

        results = self.db.list_(order='name', direction='desc')
        assert_that(results, contains(c, b, a))

    def test_sort_order(self):
        a, b, c = self.content

        results = self.db.list_(order='name', direction='asc')
        assert_that(results, contains(a, b, c))

        results = self.db.list_(order='namespace', direction='asc')
        assert_that(results, contains(c, a, b))

        assert_that(calling(self.db.list_).with_args(order='d'),
                    raises(InvalidSortParamException))

    def test_version_sort_order(self):
        a, b, c = self.content

        results = self.db.list_(order='version', direction='asc')
        assert_that(results, contains(a, b, c))

        results = self.db.list_(order='min_wazo_version', direction='asc')
        assert_that(results, contains(a, c, b))

    def test_limit(self):
        a, b, c = self.content

        results = self.db.list_(limit=2)
        assert_that(results, contains(a, b))

        results = self.db.list_(limit=1)
        assert_that(results, contains(a))

    def test_offset(self):
        a, b, c = self.content

        results = self.db.list_(offset=1)
        assert_that(results, contains(b, c))

        results = self.db.list_(offset=2)
        assert_that(results, contains(c))

    def test_limit_and_offset(self):
        a, b, c = self.content

        results = self.db.list_(limit=1, offset=1)
        assert_that(results, contains(b))
