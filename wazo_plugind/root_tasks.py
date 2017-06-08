# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from .celery import root_worker
from .helpers import exec_and_log

logger = logging.getLogger(__name__)

_publisher = None


@root_worker.app.task
def apt_get_update(uuid_):
    logger.debug('[%s] updating apt cache', uuid_)
    cmd = ['apt-get', 'update', '-q']
    p = exec_and_log(logger.debug, logger.error, cmd)
    return p.returncode == 0


@root_worker.app.task
def install(uuid_, deb):
    logger.debug('[%s] installing %s...', uuid_, deb)
    cmd = ['gdebi', '-nq', deb]
    p = exec_and_log(logger.debug, logger.error, cmd)
    return p.returncode == 0


@root_worker.app.task
def uninstall(uuid, package_name):
    logger.debug('[%s] uninstalling %s', uuid, package_name)
    cmd = ['apt-get', 'remove', '-y', package_name]
    p = exec_and_log(logger.debug, logger.error, cmd)
    return p.returncode == 0
