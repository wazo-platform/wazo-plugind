# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import subprocess
import os
from abc import ABCMeta, abstractmethod
from multiprocessing import JoinableQueue, Process

logger = logging.getLogger(__name__)


class Quit(Exception):
    pass


class Command(metaclass=ABCMeta):

    @abstractmethod
    def execute(self):
        pass


class ShellJob(Command):

    def __init__(self, cmd, *args, **kwargs):
        self._cmd = cmd
        self._args = args
        self._kwargs = kwargs

    def execute(self):
        logger.debug('executing %s as %s', self._cmd, os.getuid())
        subprocess.Popen(self._cmd, *self._args, **self._kwargs)


class QuitJob(Command):

    def execute(self):
        raise Quit()


class Worker(object):

    def __init__(self):
        self._queue = JoinableQueue()
        self._process = None

    def execute(self, cmd, *args, **kwargs):
        job = ShellJob(cmd, *args, **kwargs)
        self._do(job)

    def stop(self):
        if not self._process.is_alive():
            return

        logger.info('stopping worker process...')
        job = QuitJob()
        self._do(job)
        logger.debug('joining the worker process')
        self._process.join()

    def start(self):
        self._process = Process(target=self._run, args=(self._queue,))
        self._process.start()

    def _do(self, job):
        self._queue.put(job)
        self._queue.join()

    def _run(self, queue):
        # This method is executed in the worker process
        logger.info('starting worker process')
        try:
            while True:
                logger.debug('waiting for a job')
                command = queue.get()
                try:
                    command.execute()
                finally:
                    queue.task_done()
        except (KeyboardInterrupt, Quit):
            queue.close()
            logger.debug('worker exit')
