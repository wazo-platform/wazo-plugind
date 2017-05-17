# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from mock import Mock, sentinel as s
from xivo_bus.resources.plugins.events import (
    PluginInstallProgressEvent,
    PluginUninstallProgressEvent,
)
from ..bus import StatusPublisher


class TestStatusPublisher(TestCase):

    def setUp(self):
        self.publisher = Mock()
        self.status_publisher = StatusPublisher(self.publisher)

    def test_that_install_publishes_the_right_event(self):
        ctx = Mock(uuid=s.uuid)

        self.status_publisher.install(ctx, s.status)

        expected_event = PluginInstallProgressEvent(s.uuid, s.status)

        self.publisher.publish.assert_called_once_with(expected_event)

    def test_that_uninstall_publishes_the_right_event(self):
        ctx = Mock(uuid=s.uuid)

        self.status_publisher.uninstall(ctx, s.status)

        expected_event = PluginUninstallProgressEvent(s.uuid, s.status)

        self.publisher.publish.assert_called_once_with(expected_event)
