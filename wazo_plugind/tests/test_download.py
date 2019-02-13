# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, equal_to
from mock import Mock
from unittest import TestCase

from wazo_plugind import context, download
from wazo_plugind.config import _DEFAULT_CONFIG


class TestMarketDownloader(TestCase):

    def setUp(self):
        self._main_downloader = Mock()
        self.downloader = download._MarketDownloader(_DEFAULT_CONFIG, self._main_downloader)

    def test_already_satisfied(self):
        not_installed = {}
        old_installed = {'installed_version': '0.0.1'}
        new_installed = {'installed_version': '1.5.2'}
        matching_installed = {'installed_version': '1.5.1'}

        tests = [
            (not_installed, False),
            (old_installed, False),
            (new_installed, False),
            (matching_installed, True),
        ]

        ctx = context.Context(_DEFAULT_CONFIG, install_params={'reinstall': False})

        for plugin_info, expected in tests:
            result = self.downloader._already_satisfied(ctx, plugin_info, '1.5.1')
            assert_that(result, equal_to(expected), plugin_info)

        tests = [
            (not_installed, False),
            (old_installed, True),
            (new_installed, True),
            (matching_installed, True),
        ]

        for plugin_info, expected in tests:
            result = self.downloader._already_satisfied(ctx, plugin_info, None)
            assert_that(result, equal_to(expected), plugin_info)
