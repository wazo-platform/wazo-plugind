# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from mock import Mock
from ..service import PluginService


class TestCreate(TestCase):

    def setUp(self):
        worker = Mock()
        self.service = PluginService(worker)

    def test_installation_steps(self):
        return
