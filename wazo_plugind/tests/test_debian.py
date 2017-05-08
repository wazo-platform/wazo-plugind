# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import tempfile
from unittest import TestCase
from hamcrest import assert_that, equal_to
from jinja2 import DictLoader, Environment
from ..service import InstallContext
from ..debian import Generator
from ..config import _DEFAULT_CONFIG


class TestDebianGenerator(TestCase):

    def test_make_template_ctx_adds_metadata_and_rules_path(self):
        ctx = self.new_install_context(
            metadata={'foo': 'bar'},
            destination_plugin_path='/var/lib/foobar',
            installer_base_filename='rules',
        )
        generator = Generator()

        ctx = generator._make_template_ctx(ctx)

        expected = {'foo': 'bar',
                    'rules_path': '/var/lib/foobar/rules'}
        assert_that(ctx.template_context, equal_to(expected))

    def test_make_debian_dir(self):
        with tempfile.TemporaryDirectory() as pkgdir:
            ctx = self.new_install_context(
                pkgdir=pkgdir,
            )
            generator = Generator()

            ctx = generator._make_debian_dir(ctx)

            expected = '{}/DEBIAN'.format(pkgdir)
            assert_that(ctx.debian_dir, equal_to(expected))
            assert_that(os.path.exists(expected), 'DEBIAN dir has not been created')

    def test_generate_file(self):
        filename = 'control'
        template_name = 'control.jinja'
        loader = DictLoader({template_name: '{{ status }}'})
        with tempfile.TemporaryDirectory() as debian_dir:
            ctx = self.new_install_context(
                template_context={'status': 'SUCCESS'},
                debian_dir=debian_dir,
            )
            generator = Generator(Environment(loader=loader), {filename: template_name})

            generator._generate_file(ctx, filename)

            expected_path = os.path.join(debian_dir, filename)
            with open(expected_path) as f:
                assert_that(f.read(), equal_to('SUCCESS'))

    def new_install_context(self, **kwargs):
        ctx = InstallContext(_DEFAULT_CONFIG, 'foo', 'bar')
        for field, value in kwargs.items():
            setattr(ctx, field, value)
        return ctx
