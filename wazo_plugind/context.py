# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from functools import partial
from uuid import uuid4

logger = logging.getLogger(__name__)


class Context:
    def __init__(self, config, **kwargs):
        self.uuid = str(uuid4())
        self.config = config
        self.with_fields(**kwargs)

    def log(self, logger, msg, *args, **kwargs):
        log_msg = f'[{self.uuid}] {msg}'
        logger(log_msg, *args, **kwargs)

    def get_logger(self, logger):
        return partial(self.log, logger)

    def with_fields(self, **kwargs):
        for field, value in kwargs.items():
            setattr(self, field, value)
        return self
