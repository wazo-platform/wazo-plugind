# Copyright 2017-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_bus.publisher import BusPublisher
from xivo_bus.resources.plugins.events import (
    PluginInstallProgressEvent,
    PluginUninstallProgressEvent,
)


class Publisher(BusPublisher):
    @classmethod
    def from_config(cls, service_uuid, bus_config):
        name = 'wazo-plugind'
        return cls(name=name, service_uuid=service_uuid, **bus_config)

    def install(self, ctx, status):
        self.publish(PluginInstallProgressEvent(ctx.uuid, status))

    def install_error(self, ctx, error_id, message, details=None):
        errors = {
            'error_id': error_id,
            'message': message,
            'resource': 'plugins',
            'details': details or {},
        }
        self.publish(PluginInstallProgressEvent(ctx.uuid, 'error', errors))

    def uninstall(self, ctx, status):
        self.publish(PluginUninstallProgressEvent(ctx.uuid, status))

    def uninstall_error(self, ctx, error_id, message, details=None):
        errors = {
            'error_id': error_id,
            'message': message,
            'resource': 'plugins',
            'details': details or {},
        }
        self.publish(PluginUninstallProgressEvent(ctx.uuid, 'error', errors))
