# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import jinja2


class Generator(object):

    _debian_dir = 'DEBIAN'
    _generated_files = ['control', 'postinst', 'prerm']
    _generated_files_mod = {'postinst': 0o755, 'prerm': 0o755}

    def __init__(self, jinja_env=None, template_files=None):
        self._env = jinja_env
        self._template_files = template_files

    def generate(self, ctx):
        ctx = self._make_template_ctx(ctx)
        ctx = self._make_debian_dir(ctx)
        for filename in self._generated_files:
            ctx = self._generate_file(ctx, filename)
        return ctx

    def _make_template_ctx(self, ctx):
        installed_rules_path = os.path.join(ctx.destination_plugin_path, ctx.installer_base_filename)
        template_context = dict(ctx.metadata, rules_path=installed_rules_path)
        return ctx.with_template_context(template_context)

    def _make_debian_dir(self, ctx):
        debian_dir = os.path.join(ctx.pkgdir, self._debian_dir)
        os.mkdir(debian_dir)
        return ctx.with_debian_dir(debian_dir)

    def _generate_file(self, ctx, filename):
        file_path = os.path.join(ctx.debian_dir, filename)
        template = self._env.get_template(self._template_files[filename])
        with open(file_path, 'w') as f:
            f.write(template.render(ctx.template_context))

        mod = self._generated_files_mod.get(filename)
        if mod:
            os.chmod(file_path, mod)

        return ctx

    @classmethod
    def from_config(cls, config):
        loader = jinja2.FileSystemLoader(config['template_dir'])
        env = jinja2.Environment(loader=loader)
        template_files = {'control': config['control_template'],
                          'postinst': config['postinst_template'],
                          'prerm': config['prerm_template']}
        return cls(env, template_files)
