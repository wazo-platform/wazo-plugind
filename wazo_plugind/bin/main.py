# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
from xivo import xivo_logging
from xivo.config_helper import set_xivo_uuid, UUIDNotFound
from xivo.user_rights import change_user
from wazo_plugind import config
from wazo_plugind.controller import Controller
from wazo_plugind.root_worker import RootWorker

logger = logging.getLogger(__name__)


def main(args):
    conf = config.load_config(args)

    xivo_logging.setup_logging(
        conf['log_file'], debug=conf['debug'], log_level=conf['log_level']
    )

    os.chdir(conf['home_dir'])

    with RootWorker() as root_worker:
        if conf['user']:
            change_user(conf['user'])

        try:
            set_xivo_uuid(conf, logger)
        except UUIDNotFound:
            # handled in the controller
            pass

        controller = Controller(conf, root_worker)
        logger.debug('starting')
        controller.run()
        logger.debug('controller stopped')
