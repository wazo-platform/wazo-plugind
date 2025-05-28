# Copyright 2017-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import os

from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_file, read_config_file_hierarchy
from xivo.xivo_logging import get_log_level_by_name

_MAX_PLUGIN_FORMAT_VERSION = 2
_DAEMONNAME = 'wazo-plugind'
_DEFAULT_HTTP_PORT = 9503
_PLUGIN_DATA_DIR = 'wazo'
_HOME_DIR = '/usr/lib/wazo-plugind'
_DEFAULT_CONFIG = {
    'config_file': f'/etc/{_DAEMONNAME}/config.yml',
    'extra_config_files': f'/etc/{_DAEMONNAME}/conf.d/',
    'home_dir': _HOME_DIR,
    'download_dir': '/var/lib/wazo-plugind/downloads',
    'extract_dir': '/var/lib/wazo-plugind/tmp',
    'metadata_dir': os.path.join(_HOME_DIR, 'plugins'),
    'template_dir': os.path.join(_HOME_DIR, 'templates'),
    'backup_rules_dir': '/var/lib/wazo-plugind/rules',
    'build_dir': '_pkg',
    'control_template': 'control.jinja',
    'postinst_template': 'postinst.jinja',
    'postrm_template': 'postrm.jinja',
    'prerm_template': 'prerm.jinja',
    'plugin_data_dir': _PLUGIN_DATA_DIR,
    'default_metadata_filename': os.path.join(_PLUGIN_DATA_DIR, 'plugin.yml'),
    'default_install_filename': os.path.join(_PLUGIN_DATA_DIR, 'rules'),
    'default_debian_package_prefix': 'wazo-plugind',
    'debian_package_section': 'wazo-plugind-plugin',
    'debug': False,
    'log_level': 'info',
    'log_file': f'/var/log/{_DAEMONNAME}.log',
    'user': _DAEMONNAME,
    'market': {'host': 'apps.wazo.community'},
    'confd': {
        'host': 'localhost',
        'port': 9486,
        'version': 1.1,
        'prefix': None,
        'https': False,
    },
    'rest_api': {
        'listen': '127.0.0.1',
        'port': _DEFAULT_HTTP_PORT,
        'certificate': None,
        'private_key': None,
        'cors': {'enabled': True, 'allow_headers': ['Content-Type', 'X-Auth-Token']},
    },
    'bus': {
        'username': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': 5672,
        'exchange_name': 'wazo-headers',
        'exchange_type': 'headers',
    },
    'consul': {
        'scheme': 'http',
        'port': 8500,
    },
    'service_discovery': {
        'enabled': False,
        'advertise_address': 'auto',
        'advertise_address_interface': 'eth0',
        'advertise_port': _DEFAULT_HTTP_PORT,
        'ttl_interval': 30,
        'refresh_interval': 27,
        'retry_interval': 2,
        'extra_tags': [],
    },
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-plugind-key.yml',
    },
}


def load_config(args):
    cli_config = _parse_cli_args(args)
    file_config = read_config_file_hierarchy(ChainMap(cli_config, _DEFAULT_CONFIG))
    reinterpreted_config = _get_reinterpreted_raw_values(
        cli_config, file_config, _DEFAULT_CONFIG
    )
    service_key = _load_key_file(ChainMap(cli_config, file_config, _DEFAULT_CONFIG))
    return ChainMap(
        reinterpreted_config, cli_config, service_key, file_config, _DEFAULT_CONFIG
    )


def _load_key_file(config):
    if config['auth'].get('username') and config['auth'].get('password'):
        return {}

    key_file = parse_config_file(config['auth']['key_file'])
    return {
        'auth': {
            'username': key_file['service_id'],
            'password': key_file['service_key'],
        }
    }


def _get_reinterpreted_raw_values(*configs):
    config = ChainMap(*configs)
    return {'log_level': get_log_level_by_name(config['log_level'])}


def _parse_cli_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config-file', action='store', help='The path to the config file'
    )
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help='Log debug mesages. Override log_level',
    )
    parser.add_argument('-u', '--user', action='store', help='The owner of the process')
    parsed_args = parser.parse_args()

    result = {}
    if parsed_args.config_file:
        result['config_file'] = parsed_args.config_file
    if parsed_args.debug:
        result['debug'] = parsed_args.debug
    if parsed_args.user:
        result['user'] = parsed_args.user

    return result
