# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from mock import patch, sentinel as s

from ..service import PluginService


class TestCreate(TestCase):

    def setUp(self):
        self.service = PluginService()

    def test_installation_steps(self):
        with patch.object(self.service, 'download') as download, \
             patch.object(self.service, 'extract_to') as extract_to, \
             patch.object(self.service, 'install') as install:
            self.service.create(s.ns, s.name, s.url, s.method)

            download.assert_called_once_with(s.method, s.url)
            extract_to.assert_called_once_with(s.ns, s.name, download.return_value)
            install.assert_called_once_with(s.ns, s.name)
