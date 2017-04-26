# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import subprocess
import os
import signal
from abc import ABCMeta, abstractmethod
from multiprocessing import JoinableQueue, Process

logger = logging.getLogger(__name__)


class Quit(Exception):
    pass


class Command(metaclass=ABCMeta):

    def __str__(self):
        return self.__class__.__name__

    @abstractmethod
    def execute(self):
        pass


class ShellJob(Command):

    def __init__(self, cmd, *args, **kwargs):
        self._cmd = cmd
        self._args = args
        self._kwargs = kwargs
        self._plugins_path = '/var/lib/wazo-plugind/plugins'

    def execute(self):
        logger.debug('executing %s as %s', self._cmd, os.getuid())
        subprocess.Popen(['chattr', '-R', '+i', self._plugins_path]).wait()
        try:
            subprocess.Popen(self._cmd, *self._args, **self._kwargs).wait()
        finally:
            subprocess.Popen(['chattr', '-R', '-i', self._plugins_path]).wait()


class QuitJob(Command):

    def execute(self):
        raise Quit()


def _on_sig_term(signum, frame):
    logger.debug('Worker ignoring SIGTERM')


class Worker(object):

    def __init__(self):
        self._queue = JoinableQueue()
        self._process = None

    def execute(self, cmd, *args, **kwargs):
        job = ShellJob(cmd, *args, **kwargs)
        self._do(job)

    def stop(self):
        logger.info('stopping worker process...')
        job = QuitJob()
        self._do(job)

    def start(self):
        self._process = Process(target=self._run, args=(self._queue,))
        self._process.start()

    def _do(self, job):
        logger.debug('sending job to worker %s', job)
        self._queue.put(job)
        self._queue.join()

    def _run(self, queue):
        # This method is executed in the worker process
        logger.info('starting worker process')
        signal.signal(signal.SIGTERM, _on_sig_term)
        while True:
            logger.debug('waiting for a job')
            try:
                command = queue.get()
            except KeyboardInterrupt:
                logger.debug('worker process ignoring exit KeyboardInterrupt')
                continue

            try:
                logger.debug('executing command %s', command)
                command.execute()
            except Quit:
                logger.info('Quit received')
                break
            finally:
                logger.debug('task done')
                queue.task_done()

        logger.info('Worker exit')
