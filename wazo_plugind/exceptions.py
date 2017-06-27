# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.rest_api_helpers import APIException


class UnsupportedDownloadMethod(APIException):

    def __init__(self):
        super().__init__(status_code=501,
                         message='Unsupported download method',
                         error_id='unsupported_download_method',
                         details={})


class InvalidPackageNameException(Exception):

    _fmt = 'invalid debian package name {}'

    def __init__(self, name):
        super().__init__(self._fmt.format(name))


class InvalidMetadata(Exception):

    details = None

    def __init__(self, details):
        self.details = details


class InvalidNamespaceException(InvalidMetadata):

    _details = {
        'namespace': {
            'constraint_id': 'regex',
            'constaint': r'^[a-z0-9]+$',
            'message': 'namespace must be lowercase with letters and numbers only',
        },
    }

    def __init__(self):
        super().__init__(self._details)


class InvalidNameException(InvalidMetadata):

    _details = {
        'name': {
            'constraint_id': 'regex',
            'constaint': r'^[a-z0-9-]+$',
            'message': 'name must be lowercase with letters, numbers and dashes only',
        },
    }

    def __init__(self):
        super().__init__(self._details)


class MissingFieldException(InvalidMetadata):

    def __init__(self, field):
        details = {
            field: {
                'constraint_id': 'required',
                'constraint': {'required': True},
                'message': '"{}" is a required field'.format(field),
            },
        }
        super().__init__(details)


class InvalidPluginFormatVersion(InvalidMetadata):

    msg_fmt = 'The plugin_format_version field should be between 0 and {}'

    def __init__(self, max_plugin_format_version):
        details = {
            'plugin_format_version': {
                'constraint_id': 'limits',
                'constraint': [0, max_plugin_format_version],
                'message': self.msg_fmt.format(max_plugin_format_version),
            },
        }
        super().__init__(details)


class InvalidInstallParamException(APIException):

    def __init__(self, errors):
        super().__init__(status_code=400,
                         message='Invalid data',
                         error_id='invalid_data',
                         resource='plugins',
                         details=self.format_details(errors))

    def format_details(self, errors):
        return {
            field: info[0] if isinstance(info, list) else info
            for field, info in errors.items()
        }


class PluginNotFoundException(APIException):

    def __init__(self, namespace, name):
        super().__init__(status_code=404,
                         message='Plugin not found {}/{}'.format(namespace, name),
                         error_id='plugin_not_found',
                         resource='plugins',
                         details={'name': name, 'namespace': namespace})


class PluginAlreadyInstalled(Exception):

    _fmt = '{}/{} is already installed'

    def __init__(self, namespace, name):
        super().__init__(self._fmt.format(namespace, name))
