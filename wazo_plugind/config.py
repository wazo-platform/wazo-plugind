# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import argparse
import os

from xivo.chain_map import ChainMap
from xivo.config_helper import read_config_file_hierarchy
from xivo.xivo_logging import get_log_level_by_name


_MAX_PLUGIN_FORMAT_VERSION = 1
_DAEMONNAME = 'wazo-plugind'
_DEFAULT_HTTPS_PORT = 9503
_DEFAULT_CERT_FILE = '/usr/share/xivo-certs/server.crt'
_PLUGIN_DATA_DIR = 'wazo'
_PID_DIR = '/var/run/{}'.format(_DAEMONNAME)
_DEFAULT_CONFIG = dict(
    config_file='/etc/{}/config.yml'.format(_DAEMONNAME),
    extra_config_files='/etc/{}/conf.d/'.format(_DAEMONNAME),
    download_dir='/var/lib/wazo-plugind/downloads',
    extract_dir='/var/lib/wazo-plugind/tmp',
    metadata_dir='/usr/lib/wazo-plugind/plugins',
    template_dir='/usr/lib/wazo-plugind/templates',
    backup_rules_dir='/var/lib/wazo-plugind/rules',
    build_dir='_pkg',
    control_template='control.jinja',
    postinst_template='postinst.jinja',
    postrm_template='postrm.jinja',
    prerm_template='prerm.jinja',
    plugin_data_dir=_PLUGIN_DATA_DIR,
    default_metadata_filename=os.path.join(_PLUGIN_DATA_DIR, 'plugin.yml'),
    default_install_filename=os.path.join(_PLUGIN_DATA_DIR, 'rules'),
    default_debian_package_prefix='wazo-plugind',
    debian_package_section='wazo-plugind-plugin',
    debug=False,
    log_level='info',
    log_file='/var/log/{}.log'.format(_DAEMONNAME),
    user=_DAEMONNAME,
    market={
        'url': 'https://apps.wazo.community/index.json',
        'verify_certificate': False,
    },
    pid_file=os.path.join(_PID_DIR, '{}.pid'.format(_DAEMONNAME)),
    celery={
        'broker': 'amqp://guest:guest@localhost:5672',
        'unpriviledged': {
            'exchange_name': 'celery_plugind',
            'queue_name': 'plugind_task_queue',
            'routing_key': 'plugind.tasks',
            'pid_file': os.path.join(_PID_DIR, 'worker.pid')
        },
        'priviledged': {
            'exchange_name': 'celery_plugind_root',
            'queue_name': 'plugind_root_task_queue',
            'routing_key': 'plugind.root_tasks',
            'pid_file': os.path.join(_PID_DIR, 'root_worker.pid')
        },
    },
    rest_api={
        'https': {
            'listen': '0.0.0.0',
            'port': _DEFAULT_HTTPS_PORT,
            'certificate': _DEFAULT_CERT_FILE,
            'private_key': '/usr/share/xivo-certs/server.key',
        },
        'cors': {'enabled': True,
                 'allow_headers': ['Content-Type', 'X-Auth-Token']}
    },
    bus={
        'username': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': 5672,
        'exchange_name': 'xivo',
        'exchange_type': 'topic',
    },
    consul={
        'scheme': 'https',
        'host': 'localhost',
        'port': 8500,
        'verify': '/usr/share/xivo-certs/server.crt',
    },
    service_discovery={
        'advertise_address': 'auto',
        'advertise_address_interface': 'eth0',
        'advertise_port': _DEFAULT_HTTPS_PORT,
        'enabled': True,
        'ttl_interval': 30,
        'refresh_interval': 27,
        'retry_interval': 2,
        'extra_tags': [],
    },
    auth={
        'host': 'localhost',
        'port': 9497,
        'verify_certificate': _DEFAULT_CERT_FILE,
    }
)


def load_config(args):
    cli_config = _parse_cli_args(args)
    file_config = read_config_file_hierarchy(ChainMap(cli_config, _DEFAULT_CONFIG))
    reinterpreted_config = _get_reinterpreted_raw_values(cli_config, file_config, _DEFAULT_CONFIG)
    return ChainMap(reinterpreted_config, cli_config, file_config, _DEFAULT_CONFIG)


def _get_reinterpreted_raw_values(*configs):
    config = ChainMap(*configs)
    return dict(
        log_level=get_log_level_by_name(config['log_level']),
    )


def _parse_cli_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-file', action='store', help='The path to the config file')
    parser.add_argument('-d', '--debug', action='store_true', help='Log debug mesages. Override log_level')
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
