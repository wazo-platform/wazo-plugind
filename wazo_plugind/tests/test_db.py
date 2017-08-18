# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from contextlib import contextmanager
from unittest import TestCase
from hamcrest import assert_that, calling, contains, empty, equal_to, has_entries, raises
from mock import Mock, patch

from ..config import _DEFAULT_CONFIG
from ..db import (iin, normalize_caseless, MarketDB, MarketPluginUpdater, MarketProxy, Plugin, PluginDB,
                  _version_less_than)
from ..exceptions import InvalidSortParamException

CURRENT_WAZO_VERSION = '17.12'


class TestVersionLessThan(TestCase):

    def test_less_than(self):
        assert_that(_version_less_than('17.10', '17.10'), equal_to(False))
        assert_that(_version_less_than('17.09', '17.10'), equal_to(True))
        assert_that(_version_less_than(None, '17.10'), equal_to(True))
        assert_that(_version_less_than('17.10', None), equal_to(False))
        assert_that(_version_less_than('', None), equal_to(True))


class TestMarketPluginUpdater(TestCase):

    def setUp(self):
        self.uninstalled_plugin = Mock()
        self.uninstalled_plugin.is_installed.return_value = False
        self.plugin_db = Mock(PluginDB)
        self.plugin_db.get_plugin.return_value = self.uninstalled_plugin
        self.updater = MarketPluginUpdater(self.plugin_db, current_wazo_version=CURRENT_WAZO_VERSION)

    def test_that_the_installed_version_is_added(self):
        plugin_info = {
            'name': 'foo',
            'namespace': 'foobar',
        }

        with self.installed_plugin('foobar', 'foo', '0.0.1'):
            result = self.updater.update(plugin_info)

        assert_that(result, has_entries('installed_version', '0.0.1'))

    def test_upgradable_field_with_min_version_too_high(self):
        plugin_info = {
            'namespace': 'foobar',
            'name': 'foo',
            'versions': [
                {
                    'min_wazo_version': '17.13',
                },
            ],
        }

        result = self.updater.update(plugin_info)

        assert_that(result, has_entries('versions', contains(has_entries('upgradable', False))))

    def test_upgradable_field_with_min_version_that_is_ok(self):
        plugin_info = {
            'namespace': 'foobar',
            'name': 'foo',
            'versions': [
                {
                    'min_wazo_version': CURRENT_WAZO_VERSION,
                },
            ],
        }

        result = self.updater.update(plugin_info)

        assert_that(result, has_entries('versions', contains(has_entries('upgradable', True))))

    def test_upgradable_field_with_max_version_too_low(self):
        plugin_info = {
            'namespace': 'foobar',
            'name': 'foo',
            'versions': [
                {
                    'max_wazo_version': '17.11',
                },
            ],
        }

        result = self.updater.update(plugin_info)

        assert_that(result, has_entries('versions', contains(has_entries('upgradable', False))))

    def test_upgradable_field_with_max_version_that_is_ok(self):
        plugin_info = {
            'namespace': 'foobar',
            'name': 'foo',
            'versions': [
                {
                    'max_wazo_version': CURRENT_WAZO_VERSION,
                },
            ],
        }

        result = self.updater.update(plugin_info)

        assert_that(result, has_entries('versions', contains(has_entries('upgradable', True))))

    def test_upgradable_with_an_old_version(self):
        plugin_info = {
            'namespace': 'foobar',
            'name': 'foo',
            'versions': [
                {
                    'version': '0.0.1'
                },
            ],
        }

        with self.installed_plugin('foobar', 'foo', '0.0.2'):
            result = self.updater.update(plugin_info)

        assert_that(result, has_entries('versions', contains(has_entries('upgradable', False))))

    def test_upgradable_with_the_same_version(self):
        plugin_info = {
            'namespace': 'foobar',
            'name': 'foo',
            'versions': [
                {
                    'version': '0.0.1'
                },
            ],
        }

        with self.installed_plugin('foobar', 'foo', '0.0.1'):
            result = self.updater.update(plugin_info)

        assert_that(result, has_entries('versions', contains(has_entries('upgradable', False))))

    def test_upgradable_with_a_newer_version(self):
        plugin_info = {
            'namespace': 'foobar',
            'name': 'foo',
            'versions': [
                {
                    'version': '0.0.2'
                },
            ],
        }

        with self.installed_plugin('foobar', 'foo', '0.0.1'):
            result = self.updater.update(plugin_info)

        assert_that(result, has_entries('versions', contains(has_entries('upgradable', True))))

    @contextmanager
    def installed_plugin(self, namespace, name, version):
        metadata = {'name': name, 'namespace': namespace, 'version': version}

        mocked_plugin = Mock(Plugin, namespace=namespace, name=name)
        mocked_plugin.metadata.return_value = metadata

        self.plugin_db.get_plugin.return_value = mocked_plugin

        yield

        self.plugin_db.get_plugin.return_value = self.uninstalled_plugin


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
            {
                'name': 'a',
                'namespace': 'c',
                'tags': ['foobar'],
                'd': {},
                'author': 'me',
                'installed_version': '0.0.1',
                'versions': [
                    {
                        'version': '0.1.1',
                        'min_wazo_version': '1',
                    },
                    {
                        'version': '0.0.1',
                    },
                ],
            },
            {
                'name': 'b',
                'tags': ['pépé'],
                'd': {42: 'bar'},
                'author': 'you',
                'installed_version': None,
                'versions': [
                    {
                        'version': '0.3.0',
                        'min_wazo_version': '9999',
                    },
                    {
                        'version': '0.2.0',
                        'min_wazo_version': '3',
                    },
                    {
                        'version': '0.1.1',
                    },
                ],
            },
            {
                'namespace': 'a',
                'author': 'you & me',
                'installed_version': '0.10.0',
                'versions': [
                    {
                        'version': '0.12.0',
                        'min_wazo_version': '2',
                    },
                    {
                        'version': '0.10.5',
                        'max_wazo_version': '0',
                    },
                ],
            },
        ]
        self.market_proxy = Mock(MarketProxy)
        self.market_proxy.get_content.return_value = self.content
        self.db = MarketDB(self.market_proxy, CURRENT_WAZO_VERSION)
        self.db._updater = Mock(MarketPluginUpdater)

    def test_the_installed_param(self):
        a, b, c = self.content

        results = self.db.list_(installed=True)
        assert_that(results, contains(a, c))

    def test_list_with_strict_filter(self):
        a, b, c = self.content

        results = self.db.list_(namespace='a')
        assert_that(results, contains(c))

        results = self.db.list_(name='a', namespace='c', author='me')
        assert_that(results, contains(a))

        results = self.db.list_(name='a', namespace='c', author='you')  # Not full match on author
        assert_that(results, empty())

    def test_get(self):
        self.market_proxy.get_content.return_value = expected_result = [
            {
                'namespace': 'foo',
                'name': 'bar',
                'verions': [
                    {'version': '0.1.1'},
                    {'version': '0.0.1'},
                    {'version': '0.2.0'},
                ],
            },
        ]

        result = self.db.get('foo', 'bar')
        assert_that(result, expected_result)

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
