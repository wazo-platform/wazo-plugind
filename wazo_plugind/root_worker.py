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

    name = 'base'

    def __init__(self):
        self._command_queue = Queue()
        self._result_queue = Queue()
        self._stop_requested = Event()
        self._process = Process(target=_run, args=(self._command_queue,
                                                   self._result_queue,
                                                   self._stop_requested))

    def run(self):
        logger.info('starting %s worker', self.name)
        self._process.start()

    def stop(self):
        logger.info('stopping %s worker', self.name)
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

        logger.info('%s worker stopped', self.name)

    def send_cmd_and_wait(self, cmd, *args, **kwargs):
        if not self._process.is_alive():
            logger.info('%s process is dead quitting', self.name)
            # kill the main thread
            os.kill(os.getpid(), signal.SIGTERM)
            # shutdown the current thread execution so that executor.shutdown does not block
            sys.exit(1)

        self._command_queue.put((cmd, args, kwargs))
        return self._result_queue.get()


class RootWorker(BaseWorker):

    name = 'root'

    def apt_get_update(self, *args, **kwargs):
        return self.send_cmd_and_wait('update', *args, **kwargs)

    def install(self, *args, **kwargs):
        return self.send_cmd_and_wait('install', *args, **kwargs)

    def uninstall(self, *args, **kwargs):
        return self.send_cmd_and_wait('uninstall', *args, **kwargs)


class _CommandExecutor(object):

    def __init__(self):
        self._fn_map = {
            'update': self._apt_get_update,
            'install': self._install,
            'uninstall': self._uninstall,
        }

    def execute(self, cmd, *args, **kwargs):
        fn = self._fn_map.get(cmd)
        if not fn:
            logger.info('root worker received an unknown command "%s"', cmd.name)
            return

        try:
            return fn(*args, **kwargs)
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
            cmd, args, kwargs = command_queue.get(timeout=0.1)
        except (KeyboardInterrupt, Empty, Exception):
            continue

        result = executor.execute(cmd, *args, **kwargs)
        result_queue.put(result)

    logger.info('root worker done')
