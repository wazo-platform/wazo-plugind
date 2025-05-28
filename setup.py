#!/usr/bin/env python3
# Copyright 2017-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from setuptools import find_packages, setup

setup(
    name='wazo-plugind',
    version='0.1',
    author='Wazo Authors',
    author_email='dev@wazo.community',
    url='http://wazo.community',
    packages=find_packages(),
    scripts=['bin/wazo-plugind'],
    package_data={'wazo_plugind.openapi': ['*.yml']},
    include_package_data=True,
    zip_safe=False,
)
