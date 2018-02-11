# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import subprocess
import logging
import jinja2

logger = logging.getLogger(__name__)


class PackageDB(object):

    _package_and_section_format = "${binary:Package} ${Section}\n"

    def __init__(self, package_section_generator=None):
        self._package_section_generator = package_section_generator or self._list_packages

    def list_installed_packages(self, selected_section=None):
        def filter_(name, section):
            if not selected_section:
                return True
            return selected_section == section

        for line in self._package_section_generator():
            debian_package_name, _, section = line.partition(' ')
            if not filter_(debian_package_name, section):
                continue
            yield debian_package_name

    @classmethod
    def _list_packages(cls):
        cmd = ['dpkg-query', '-W', '-f={}'.format(cls._package_and_section_format)]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, _ = p.communicate()
        for line in out.decode('utf-8').split('\n'):
            yield line


class Generator(object):

    _debian_dir = 'DEBIAN'
    _generated_files = ['control', 'postinst', 'prerm', 'postrm']
    _generated_files_mod = {'postinst': 0o755, 'prerm': 0o755, 'postrm': 0o755}
    _debian_package_name_fmt = 'wazo-plugind-{name}-{namespace}'

    def __init__(self, jinja_env=None, template_files=None, section=None,
                 metadata_dir=None, rules_path=None, backup_rules_dir=None):
        self._env = jinja_env
        self._template_files = template_files
        self._section = section
        self._metadata_dir = metadata_dir
        self._rules_path = rules_path
        self._backup_rules_dir = backup_rules_dir

    def generate(self, ctx):
        ctx = self._make_template_ctx(ctx)
        ctx = self._make_debian_dir(ctx)
        for filename in self._generated_files:
            ctx = self._generate_file(ctx, filename)
        return ctx

    def _add_debian_depends_from_depends(self, ctx):
        depends = ctx.metadata.get('depends')
        if not isinstance(depends, (list, tuple)):
            return ctx

        deps = ctx.metadata.get('debian_depends', [])
        for dependency in depends:
            deb_dep = self._debian_package_name_fmt.format(**dependency)
            deps.append(deb_dep)
        ctx.metadata['debian_depends'] = deps
        ctx.log(logger.debug, 'Depends:\n%s', depends)
        ctx.log(logger.debug, 'Generated debian depends:\n%s', ctx.metadata['debian_depends'])

        return ctx

    def _make_template_ctx(self, ctx):
        ctx = self._add_debian_depends_from_depends(ctx)
        template_context = dict(ctx.metadata,
                                rules_path=self._generate_rules_path(ctx),
                                backup_rules_path=self._generate_backup_rules_path(ctx),
                                debian_package_section=self._section)
        return ctx.with_fields(template_context=template_context)

    def _make_debian_dir(self, ctx):
        debian_dir = os.path.join(ctx.pkgdir, self._debian_dir)
        os.mkdir(debian_dir)
        return ctx.with_fields(debian_dir=debian_dir)

    def _generate_file(self, ctx, filename):
        file_path = os.path.join(ctx.debian_dir, filename)
        template = self._env.get_template(self._template_files[filename])
        with open(file_path, 'w') as f:
            content = template.render(ctx.template_context)
            ctx.log(logger.debug, 'generated %s\n%s', file_path, content)
            f.write(content)

        mod = self._generated_files_mod.get(filename)
        if mod:
            os.chmod(file_path, mod)

        return ctx

    def _generate_rules_path(self, ctx):
        return os.path.join(self._metadata_dir, ctx.namespace, ctx.name, self._rules_path)

    def _generate_backup_rules_path(self, ctx):
        filename = 'rules.{}.{}'.format(ctx.name, ctx.namespace)
        return os.path.join(self._backup_rules_dir, filename)

    def _generate_metadata_path(self, ctx):
        return os.path.join(self._metadata_dir, ctx.namespace, ctx.name, self._metadata_path)

    @classmethod
    def from_config(cls, config):
        loader = jinja2.FileSystemLoader(config['template_dir'])
        env = jinja2.Environment(loader=loader)
        template_files = {'control': config['control_template'],
                          'postinst': config['postinst_template'],
                          'postrm': config['postrm_template'],
                          'prerm': config['prerm_template']}
        debian_section = config['debian_package_section']
        metadata_dir = config['metadata_dir']
        rules_path = config['default_install_filename']
        backup_rules_dir = config['backup_rules_dir']
        return cls(env, template_files, debian_section, metadata_dir, rules_path, backup_rules_dir)
