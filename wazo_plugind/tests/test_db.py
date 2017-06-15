# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, equal_to
from mock import patch

from ..config import _DEFAULT_CONFIG
from ..db import Plugin


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
