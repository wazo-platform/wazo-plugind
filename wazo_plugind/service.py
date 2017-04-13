# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

logger = logging.getLogger(__name__)


class PluginService(object):

    def create(self, namespace, name, url, method):
        logger.debug('installing %s/%s from %s [%s]...', namespace, name, url, method)
        return {}
