# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import argparse

from xivo.chain_map import ChainMap
from xivo.config_helper import read_config_file_hierarchy
from xivo.http_helpers import DEFAULT_CIPHERS
from xivo.xivo_logging import get_log_level_by_name


_DAEMONNAME = 'wazo-plugind'
_DEFAULT_HTTPS_PORT = 9503
_DEFAULT_CERT_FILE = '/usr/share/xivo-certs/server.crt'
_DEFAULT_CONFIG = dict(
    config_file='/etc/{}/config.yml'.format(_DAEMONNAME),
    extra_config_files='/etc/{}/conf.d/'.format(_DAEMONNAME),
    debug=False,
    foreground=False,
    log_level='info',
    log_file='/var/log/{}.log'.format(_DAEMONNAME),
    user=_DAEMONNAME,
    pid_file='/var/run/{}/{}.pid'.format(_DAEMONNAME, _DAEMONNAME),
    rest_api={
        'https': {
            'listen': '0.0.0.0',
            'port': _DEFAULT_HTTPS_PORT,
            'certificate': _DEFAULT_CERT_FILE,
            'private_key': '/usr/share/xivo-certs/server.key',
            'ciphers': DEFAULT_CIPHERS,
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
    parser.add_argument('-f', '--foreground', action='store_true', help='Execute in foreground')
    parser.add_argument('-u', '--user', action='store', help='The owner of the process')
    parsed_args = parser.parse_args()

    result = {}
    if parsed_args.config_file:
        result['config_file'] = parsed_args.config_file
    if parsed_args.debug:
        result['debug'] = parsed_args.debug
    if parsed_args.foreground:
        result['foreground'] = parsed_args.foreground
    if parsed_args.user:
        result['user'] = parsed_args.user

    return result
