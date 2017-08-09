# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
from multiprocessing import Process, Queue
from .helpers import exec_and_log

logger = logging.getLogger(__name__)


class RootWorker(object):

    def __init__(self):
        self._command_queue = Queue()
        self._result_queue = Queue()
        self._process = Process(target=_run, args=(self._command_queue, self._result_queue))

    def run(self):
        logger.info('starting root worker')
        self._process.start()

    def stop(self):
        logger.info('stopping root worker')
        # unblock the command_queue in the worker
        cmd = _Command('stop')
        try:
            self._command_queue.put(cmd)
        except AssertionError:
            # The queue has already been closed
            pass

        # close the command queue and wait for all messages to be processed
        self._command_queue.close()
        self._command_queue.join_thread()

        self._result_queue.close()
        self._result_queue.join_thread()

        # wait for the worker process to stop
        if self._process.is_alive():
            self._process.join()

        logger.info('root worker stopped')

    def apt_get_update(self, *args, **kwargs):
        cmd = _Command('update', *args, **kwargs)
        return self._send_cmd_and_wait(cmd)

    def install(self, *args, **kwargs):
        cmd = _Command('install', *args, **kwargs)
        return self._send_cmd_and_wait(cmd)

    def uninstall(self, *args, **kwargs):
        cmd = _Command('uninstall', *args, **kwargs)
        return self._send_cmd_and_wait(cmd)

    def _send_cmd_and_wait(self, cmd):
        self._command_queue.put(cmd)
        return self._result_queue.get()


class _Command(object):

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs


class _CommandExecutor(object):

    def __init__(self):
        self._fn_map = {
            'update': self._apt_get_update,
            'install': self._install,
            'uninstall': self._uninstall,
            'stop': self._stop,
        }

    def execute(self, cmd):
        fn = self._fn_map.get(cmd.name)
        if not fn:
            logger.info('root worker received an unknown command "%s"', cmd.name)
            return

        try:
            return fn(*cmd.args, **cmd.kwargs)
        except Exception:
            logger.exception('Exception caugth in root worker process')

    def _apt_get_update(self, uuid_):
        logger.debug('[%s] updating apt cache', uuid_)
        cmd = ['apt-get', 'update', '-q']
        p = exec_and_log(logger.debug, logger.error, cmd)
        return p.returncode == 0

    def _install(self, uuid_, deb):
        logger.debug('[%s] installing %s...', uuid_, deb)
        cmd = ['gdebi', '-nq', deb]
        p = exec_and_log(logger.debug, logger.error, cmd)
        return p.returncode == 0

    def _uninstall(self, uuid, package_name):
        logger.debug('[%s] uninstalling %s', uuid, package_name)
        cmd = ['apt-get', 'remove', '-y', package_name]
        p = exec_and_log(logger.debug, logger.error, cmd)
        return p.returncode == 0

    def _stop(self):
        return True


def _run(command_queue, result_queue):
    logger.info('root worker started')
    os.setsid()

    executor = _CommandExecutor()
    while True:
        try:
            command_data = command_queue.get()
        except (OSError, KeyboardInterrupt):
            # The queue has been closed. The process should exit
            break

        result = executor.execute(command_data)
        result_queue.put(result)

    logger.info('root worker done')
