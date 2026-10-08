# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import shutil
import subprocess
import tempfile
from unittest import TestCase

from hamcrest import assert_that, contains_string, equal_to, is_
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')


class PackageScriptsTestCase(TestCase):
    """Run the generated maintainer scripts the way dpkg calls them."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.rules_path = os.path.join(root, 'usr', 'wazo', 'rules')
        self.backup_rules_path = os.path.join(root, 'var', 'rules', 'rules.foo.bar')
        self.calls_log = os.path.join(root, 'calls.log')
        self.bin_dir = os.path.join(root, 'bin')
        os.makedirs(os.path.dirname(self.rules_path))
        os.makedirs(self.bin_dir)
        for tool in ('mkdir', 'cp', 'rm'):
            tool_path = shutil.which(tool)
            assert tool_path is not None, f'{tool} is required to run the tests'
            os.symlink(tool_path, os.path.join(self.bin_dir, tool))
        self._env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    def write_rules(self, path, exit_codes=None):
        exit_codes = exit_codes or {}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write('#!/bin/sh\n')
            f.write(f'echo "$1" >> {self.calls_log}\n')
            for action, code in exit_codes.items():
                f.write(f'[ "$1" = {action} ] && exit {code}\n')
            f.write('exit 0\n')
        os.chmod(path, 0o755)

    def install_py3clean(self, exit_code=0):
        path = os.path.join(self.bin_dir, 'py3clean')
        with open(path, 'w') as f:
            f.write('#!/bin/sh\n')
            f.write(f'echo "py3clean $*" >> {self.calls_log}\n')
            f.write(f'exit {exit_code}\n')
        os.chmod(path, 0o755)

    def run_script(self, name, action, plugin_format_version=1, ships_python=False):
        content = self._env.get_template(f'{name}.jinja').render(
            rules_path=self.rules_path,
            backup_rules_path=self.backup_rules_path,
            plugin_format_version=plugin_format_version,
            debian_package_name='wazo-plugind-foo-bar',
            ships_python=ships_python,
        )
        script_path = os.path.join(self._tmp.name, name)
        with open(script_path, 'w') as f:
            f.write(content)
        os.chmod(script_path, 0o755)
        # a private PATH: a py3clean installed on the machine running the
        # tests must not be found unless the test installs a fake one
        return subprocess.run(
            ['/bin/sh', script_path, action],
            capture_output=True,
            text=True,
            env={'PATH': self.bin_dir},
        )

    def calls(self):
        if not os.path.exists(self.calls_log):
            return []
        with open(self.calls_log) as f:
            return f.read().splitlines()


class TestPrerm(PackageScriptsTestCase):
    def test_remove_backs_up_the_rules_and_uninstalls(self):
        self.write_rules(self.rules_path)

        result = self.run_script('prerm', 'remove')

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to(['uninstall']))
        assert_that(os.path.exists(self.backup_rules_path), is_(True))

    def test_remove_still_succeeds_when_uninstall_fails(self):
        self.write_rules(self.rules_path, {'uninstall': 3})

        result = self.run_script('prerm', 'remove')

        assert_that(result.returncode, equal_to(0))
        assert_that(os.path.exists(self.backup_rules_path), is_(True))
        assert_that(result.stderr, contains_string('uninstall failed'))

    def test_remove_still_succeeds_when_the_rules_file_is_missing(self):
        result = self.run_script('prerm', 'remove')

        assert_that(result.returncode, equal_to(0))
        assert_that(result.stderr, contains_string('not found'))


class TestPrermPythonBytecode(PackageScriptsTestCase):
    def test_remove_cleans_bytecode_after_the_uninstall_action(self):
        self.write_rules(self.rules_path)
        self.install_py3clean()

        result = self.run_script('prerm', 'remove', ships_python=True)

        assert_that(result.returncode, equal_to(0))
        # uninstall can import the plugin and write bytecode again: clean last
        assert_that(
            self.calls(), equal_to(['uninstall', 'py3clean -p wazo-plugind-foo-bar'])
        )

    def test_upgrade_cleans_bytecode(self):
        self.install_py3clean()

        result = self.run_script('prerm', 'upgrade', ships_python=True)

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to(['py3clean -p wazo-plugind-foo-bar']))

    def test_bytecode_is_cleaned_even_when_the_rules_file_is_missing(self):
        self.install_py3clean()

        result = self.run_script('prerm', 'remove', ships_python=True)

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to(['py3clean -p wazo-plugind-foo-bar']))

    def test_bytecode_is_not_cleaned_for_a_package_without_python(self):
        self.write_rules(self.rules_path)
        self.install_py3clean()

        result = self.run_script('prerm', 'remove', ships_python=False)

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to(['uninstall']))

    def test_remove_succeeds_when_py3clean_fails(self):
        self.write_rules(self.rules_path)
        self.install_py3clean(exit_code=2)

        result = self.run_script('prerm', 'remove', ships_python=True)

        assert_that(result.returncode, equal_to(0))
        assert_that(result.stderr, contains_string('py3clean failed'))

    def test_remove_succeeds_when_py3clean_is_not_installed(self):
        self.write_rules(self.rules_path)

        result = self.run_script('prerm', 'remove', ships_python=True)

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to(['uninstall']))


class TestPostrm(PackageScriptsTestCase):
    def test_remove_runs_the_postrm_action_of_the_backed_up_rules(self):
        self.write_rules(self.backup_rules_path)

        result = self.run_script('postrm', 'remove')

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to(['postrm']))

    def test_purge_after_remove_succeeds_and_cleans_the_backup(self):
        self.write_rules(self.rules_path)
        self.run_script('prerm', 'remove')

        remove = self.run_script('postrm', 'remove')
        purge = self.run_script('postrm', 'purge')

        assert_that(remove.returncode, equal_to(0))
        assert_that(purge.returncode, equal_to(0))
        assert_that(self.calls(), equal_to(['uninstall', 'postrm']))
        assert_that(os.path.exists(self.backup_rules_path), is_(False))

    def test_purge_succeeds_when_the_backup_rules_are_already_gone(self):
        result = self.run_script('postrm', 'purge')

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to([]))

    def test_remove_succeeds_when_the_backup_rules_are_missing(self):
        result = self.run_script('postrm', 'remove')

        assert_that(result.returncode, equal_to(0))
        assert_that(result.stderr, contains_string('not found'))

    def test_remove_succeeds_when_the_rules_postrm_fails(self):
        self.write_rules(self.backup_rules_path, {'postrm': 5})

        result = self.run_script('postrm', 'remove')

        assert_that(result.returncode, equal_to(0))
        assert_that(result.stderr, contains_string('postrm failed'))

    def test_purge_still_cleans_the_backup_after_a_failed_postrm(self):
        self.write_rules(self.backup_rules_path, {'postrm': 5})
        self.run_script('postrm', 'remove')

        purge = self.run_script('postrm', 'purge')

        assert_that(purge.returncode, equal_to(0))
        assert_that(os.path.exists(self.backup_rules_path), is_(False))

    def test_remove_can_be_retried(self):
        self.write_rules(self.backup_rules_path)

        first = self.run_script('postrm', 'remove')
        second = self.run_script('postrm', 'remove')

        assert_that(first.returncode, equal_to(0))
        assert_that(second.returncode, equal_to(0))

    def test_rules_postrm_is_skipped_for_plugin_format_version_0(self):
        self.write_rules(self.backup_rules_path)

        result = self.run_script('postrm', 'remove', plugin_format_version=0)

        assert_that(result.returncode, equal_to(0))
        assert_that(self.calls(), equal_to([]))

    def test_unknown_action_fails(self):
        result = self.run_script('postrm', 'bogus')

        assert_that(result.returncode, equal_to(1))
