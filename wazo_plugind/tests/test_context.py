# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from hamcrest import assert_that, equal_to
from unittest.mock import Mock, sentinel as s
from wazo_test_helpers.hamcrest.uuid_ import uuid_

from ..context import Context


class TestContext(TestCase):
    def test_context_initialization(self):
        config = {}

        ctx = Context(config, foo='bar')

        assert_that(ctx.config, equal_to(config))
        assert_that(ctx.uuid, uuid_())
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

        expected_msg = f'[{ctx.uuid}] my log %s'
        logger_debug.assert_called_once_with(expected_msg, s.var)

    def test_get_logger(self):
        main_logger = Mock()

        ctx = Context({})
        logger = ctx.get_logger(main_logger)
        logger('test')

        main_logger.assert_called_once_with(f'[{ctx.uuid}] test')
