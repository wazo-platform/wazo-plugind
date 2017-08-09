# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import signal
import os
import sys
from multiprocessing import Event, Process, Queue
from queue import Empty
from .helpers import exec_and_log

logger = logging.getLogger(__name__)


class BaseWorker(object):

    def __init__(self):
        self._command_queue = Queue()
        self._result_queue = Queue()
        self._stop_requested = Event()
        self._process = Process(target=_run, args=(self._command_queue,
                                                   self._result_queue,
                                                   self._stop_requested))

    def run(self):
        logger.info('starting root worker')
        self._process.start()

    def stop(self):
        logger.info('stopping root worker')
        # unblock the command_queue in the worker
        self._stop_requested.set()

        # close both queues
        self._command_queue.close()
        self._command_queue.join_thread()
        self._result_queue.close()
        self._result_queue.join_thread()

        # wait for the worker process to stop
        if self._process.is_alive():
            self._process.join()

        logger.info('root worker stopped')

    def send_cmd_and_wait(self, cmd):
        if not self._process.is_alive():
            logger.info('root process is dead quitting')
            # kill the main thread
            os.kill(os.getpid(), signal.SIGTERM)
            # shutdown the current thread execution so that executor.shutdown does not block
            sys.exit(1)

        self._command_queue.put(cmd)
        return self._result_queue.get()


class RootWorker(BaseWorker):

    def apt_get_update(self, *args, **kwargs):
        cmd = _Command('update', *args, **kwargs)
        return self.send_cmd_and_wait(cmd)

    def install(self, *args, **kwargs):
        cmd = _Command('install', *args, **kwargs)
        return self.send_cmd_and_wait(cmd)

    def uninstall(self, *args, **kwargs):
        cmd = _Command('uninstall', *args, **kwargs)
        return self.send_cmd_and_wait(cmd)


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


def _ignore_sigterm(signum, frame):
    logger.info('root worker is ignoring a SIGTERM')


def _run(command_queue, result_queue, stop_requested):
    logger.info('root worker started')
    os.setsid()
    signal.signal(signal.SIGTERM, _ignore_sigterm)

    executor = _CommandExecutor()
    while not stop_requested.is_set():
        try:
            command_data = command_queue.get(timeout=0.1)
        except (KeyboardInterrupt, Empty, Exception):
            continue

        result = executor.execute(command_data)
        result_queue.put(result)

    logger.info('root worker done')
