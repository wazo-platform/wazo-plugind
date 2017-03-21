# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from xivo import xivo_logging
from xivo.daemonize import pidfile_context
from xivo.user_rights import change_user
from wazo_plugind import config
from wazo_plugind.controller import Controller

logger = logging.getLogger(__name__)


def main(args):
    conf = config.load_config(args)

    xivo_logging.setup_logging(conf['log_file'], conf['foreground'], conf['debug'], conf['log_level'])

    if conf['user']:
        change_user(conf['user'])

    controller = Controller(conf)
    with pidfile_context(conf['pid_file'], conf['foreground']):
        logger.debug('starting')
        controller.run()
        logger.debug('%s', conf)
    logger.debug('done')
