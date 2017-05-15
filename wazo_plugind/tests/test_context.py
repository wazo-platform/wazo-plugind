# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, equal_to
from mock import Mock, sentinel as s
from xivo_test_helpers.hamcrest.uuid import uuid

from ..context import Context


class TestContext(TestCase):

    def test_context_initialization(self):
        config = {}

        ctx = Context(config, foo='bar')

        assert_that(ctx.config, equal_to(config))
        assert_that(ctx.uuid, uuid())
        assert_that(ctx.foo, equal_to('bar'))

    def test_with_fields(self):
        ctx = Context({})

        ctx = ctx.with_fields(one='test', foo='bar')

        assert_that(ctx.one, equal_to('test'))
        assert_that(ctx.foo, equal_to('bar'))

    def test_that_log_adds_the_uuid(self):
        ctx = Context({})
        logger_debug = Mock()

        ctx.log(logger_debug, 'my log %s', s.var)

        expected_msg = '[{}] my log %s'.format(ctx.uuid)
        logger_debug.assert_called_once_with(expected_msg, s.var)

    def test_get_logger(self):
        main_logger = Mock()

        ctx = Context({})
        logger = ctx.get_logger(main_logger)
        logger('test')

        main_logger.assert_called_once_with('[{}] test'.format(ctx.uuid))
