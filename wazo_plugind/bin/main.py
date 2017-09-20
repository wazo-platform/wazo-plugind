# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
from xivo import xivo_logging
from xivo.config_helper import set_xivo_uuid, UUIDNotFound
from xivo.daemonize import pidfile_context
from xivo.user_rights import change_user
from wazo_plugind import config
from wazo_plugind.controller import Controller
from wazo_plugind.root_worker import RootWorker

logger = logging.getLogger(__name__)

FOREGROUND = True  # Always in foreground systemd takes care of daemonizing


def main(args):
    conf = config.load_config(args)

    xivo_logging.setup_logging(conf['log_file'], FOREGROUND, conf['debug'], conf['log_level'])

    os.environ['HOME'] = conf['home_dir']

    with RootWorker() as root_worker:
        if conf['user']:
            change_user(conf['user'])

        try:
            set_xivo_uuid(conf, logger)
        except UUIDNotFound:
            # handled in the controller
            pass

        controller = Controller(conf, root_worker)
        with pidfile_context(conf['pid_file'], FOREGROUND):
            logger.debug('starting')
            controller.run()
            logger.debug('controller stopped')
        logger.debug('done')
