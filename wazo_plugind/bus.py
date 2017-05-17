# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import kombu
import logging
import xivo_bus
from functools import partial
from xivo_bus.resources.plugins.events import (
    PluginInstallProgressEvent,
    PluginUninstallProgressEvent,
)

logger = logging.getLogger(__name__)


class StatusPublisher(object):

    def __init__(self, publisher):
        self._publisher = publisher

    def install(self, ctx, status):
        ctx.log(logger.debug, 'publishing new install status: %s', status)
        return self._publish(PluginInstallProgressEvent, ctx, status)

    def uninstall(self, ctx, status):
        ctx.log(logger.debug, 'publishing new uninstall status: %s', status)
        return self._publish(PluginUninstallProgressEvent, ctx, status)

    def _publish(self, Event, ctx, status):
        event = Event(ctx.uuid, status)
        self._publisher.publish(event)

    def run(self):
        logger.info('status publisher starting')
        self._publisher.run()

    def stop(self):
        logger.info('status publisher stoping')
        self._publisher.stop()

    @classmethod
    def from_config(cls, config):
        uuid = config.get('uuid')
        bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(**config['bus'])
        exchange_name = config['bus']['exchange_name']
        exchange_type = config['bus']['exchange_type']
        publisher_fcty = partial(_new_publisher, uuid, bus_url, exchange_name, exchange_type)
        publisher = xivo_bus.PublishingQueue(publisher_fcty)
        return cls(publisher)


def _new_publisher(uuid, url, exchange_name, exchange_type):
    bus_connection = kombu.Connection(url)
    bus_exchange = kombu.Exchange(exchange_name, type=exchange_type)
    bus_producer = kombu.Producer(bus_connection, exchange=bus_exchange, auto_declare=True)
    bus_marshaler = xivo_bus.Marshaler(uuid)
    return xivo_bus.Publisher(bus_producer, bus_marshaler)
