# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, calling, equal_to, has_properties
from mock import Mock, patch, sentinel as s
from xivo_test_helpers.hamcrest.raises import raises

from ..db import MarketDB, Plugin
from ..config import _DEFAULT_CONFIG
from ..exceptions import APIException, PluginNotFoundException
from ..service import PluginService


class TestPluginService(TestCase):

    def setUp(self):
        self._publisher = Mock()
        self._worker = Mock()
        self._executor = Mock()
        self._plugin_db = Mock()
        self._version_finder = Mock()
        self._service = PluginService(
            _DEFAULT_CONFIG,
            self._publisher,
            self._worker,
            self._executor,
            plugin_db=self._plugin_db,
            wazo_version_finder=self._version_finder,
        )

    def test_get_from_market(self):
        market_db = Mock(MarketDB)
        market_db.list_.return_value = [s.expected_result]

        with patch.object(self._service, '_new_market_db', return_value=market_db):
            result = self._service.get_from_market(s.market_proxy, 'namespace', 'name')

        assert_that(result, equal_to(s.expected_result))
        market_db.list_.assert_called_once_with(namespace='namespace', name='name')

    def test_get_from_market_no_matching_plugin(self):
        market_db = Mock(MarketDB)
        market_db.list_.return_value = []

        with patch.object(self._service, '_new_market_db', return_value=market_db):
            assert_that(
                calling(self._service.get_from_market).with_args(s.market_proxy, 'namespace', 'name'),
                raises(PluginNotFoundException),
            )

    def test_get_plugin_metadata(self):
        namespace, name = 'foobar', 'someplugin'
        valid_plugin = Plugin(_DEFAULT_CONFIG, namespace, name)
        valid_plugin._metadata = s.metadata
        self._plugin_db.get_plugin.return_value = valid_plugin

        result = self._service.get_plugin_metadata(namespace, name)

        assert_that(result, equal_to(s.metadata))

    def test_get_plugin_metadata_not_installed(self):
        uninstalled_plugin = Mock(is_installed=Mock(return_value=False))
        self._plugin_db.get_plugin.return_value = uninstalled_plugin

        assert_that(
            calling(self._service.get_plugin_metadata).with_args(s.namespace, s.name),
            raises(APIException).matching(
                has_properties('status_code', 404,
                               'id_', 'plugin_not_found',
                               'resource', 'plugins')
            ),
        )
