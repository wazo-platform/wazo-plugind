# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import random
import tempfile
from unittest import TestCase
from string import ascii_lowercase
from operator import itemgetter
from hamcrest import assert_that, contains_inanyorder, equal_to
from mock import sentinel as s
from jinja2 import DictLoader, Environment
from ..context import Context
from ..debian import Generator, PackageDB
from ..config import _DEFAULT_CONFIG


def random_string(min, max):
    length = random.randint(min, max)
    valid_characters = ascii_lowercase + '-'
    return ''.join(random.choice(valid_characters) for _ in range(length))


class TestPackageDB(TestCase):
    def test_that_list_installed_packages_returns_a_list_of_package_and_section(self):
        packages_and_sections = [
            (random_string(5, 30), random_string(3, 15)) for _ in range(10)
        ]

        def generator():
            for package, section in packages_and_sections:
                yield '{} {}'.format(package, section)

        db = PackageDB(generator)

        installed_packages_and_sections = db.list_installed_packages()

        expected = [package for package, section in packages_and_sections]
        assert_that(installed_packages_and_sections, contains_inanyorder(*expected))

    def test_that_list_installed_package_can_filter_by_section(self):
        section = 'wazo-plugind-plugins'
        packages_and_sections = [
            (random_string(5, 30), random_string(3, 15)),
            (random_string(5, 30), section),
            (random_string(5, 30), section),
            (random_string(5, 30), random_string(3, 15)),
            (random_string(5, 30), random_string(3, 15)),
            (random_string(5, 30), random_string(3, 15)),
            (random_string(5, 30), section),
        ]
        expected = [name for name, _ in itemgetter(1, 2, 6)(packages_and_sections)]

        def generator():
            for package, section in packages_and_sections:
                yield '{} {}'.format(package, section)

        db = PackageDB(generator)

        installed_packages_and_sections = db.list_installed_packages(section)

        assert_that(installed_packages_and_sections, contains_inanyorder(*expected))


class TestDebianGenerator(TestCase):
    def test_make_template_ctx_adds_all_necessary_fields(self):
        depends = [
            {'namespace': 'foobar', 'name': 'baz'},
            {'namespace': 'foobar', 'name': 'foobaz'},
        ]
        ctx = Context(
            _DEFAULT_CONFIG,
            namespace='foobar',
            name='foo',
            metadata={'foo': 'bar', 'depends': depends},
            destination_plugin_path='/var/lib/foobar',
            installer_base_filename='wazo/rules',
        )

        generator = Generator(
            metadata_dir='/usr/lib/wazo-plugind',
            rules_path='wazo/rules',
            section=s.section,
            backup_rules_dir='/var/lib/wazo-plugind/rules',
        )

        ctx = generator._make_template_ctx(ctx)

        expected = {
            'foo': 'bar',
            'depends': depends,
            'debian_depends': ['wazo-plugind-baz-foobar', 'wazo-plugind-foobaz-foobar'],
            'rules_path': '/usr/lib/wazo-plugind/foobar/foo/wazo/rules',
            'debian_package_section': s.section,
            'backup_rules_path': '/var/lib/wazo-plugind/rules/rules.foo.foobar',
        }
        assert_that(ctx.template_context, equal_to(expected))

    def test_make_debian_dir(self):
        with tempfile.TemporaryDirectory() as pkgdir:
            ctx = Context(_DEFAULT_CONFIG, pkgdir=pkgdir)
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
            ctx = Context(
                _DEFAULT_CONFIG,
                template_context={'status': 'SUCCESS'},
                debian_dir=debian_dir,
            )
            generator = Generator(Environment(loader=loader), {filename: template_name})

            generator._generate_file(ctx, filename)

            expected_path = os.path.join(debian_dir, filename)
            with open(expected_path) as f:
                assert_that(f.read(), equal_to('SUCCESS'))
