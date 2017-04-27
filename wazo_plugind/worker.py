# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import subprocess
import signal
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
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


class InstallJob(Command):

    def __init__(self, ctx):
        self._ctx = ctx

    def execute(self):
        with self.immutable_directory(self._ctx.plugin_dir):
            subprocess.Popen(
                [self._ctx.installer_path, 'install'],
                cwd=self._ctx.plugin_path,
            ).wait()

    @contextmanager
    def immutable_directory(self, directory):
        subprocess.Popen(['chattr', '-R', '+i', directory]).wait()
        try:
            yield
        finally:
            subprocess.Popen(['chattr', '-R', '-i', directory]).wait()


class QuitJob(Command):

    def execute(self):
        raise Quit()


def _on_sig_term(signum, frame):
    logger.debug('Worker ignoring SIGTERM')


class Worker(object):

    def __init__(self):
        self._queue = JoinableQueue()
        self._process = None

    def install(self, ctx):
        job = InstallJob(ctx)
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
