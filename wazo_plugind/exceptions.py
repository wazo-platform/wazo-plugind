# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.rest_api_helpers import APIException


class CommandExecutionFailed(Exception):

    def __init__(self, command, return_code):
        self._command = command
        self._return_code = return_code

    def __str__(self):
        return '{} returned {}'.format(self._command, self._return_code)


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


class InvalidVersionException(Exception):

    _fmt = 'invalid version {}'

    def __init__(self, version_string):
        super().__init__(self._fmt.format(version_string))


class InvalidSortParamException(APIException):

    _fmt = '"{}" values are not orderable'

    def __init__(self, column):
        super().__init__(status_code=400,
                         message='Invalid sort parameters',
                         error_id='invalid_sort_params',
                         resource='market',
                         details={column: {'constraint_id': 'orderable',
                                           'message': self._fmt.format(column)}})


class _MarshmallowDetailFormatter:

    def format_details(self, errors):
        return {
            field: self._format_errors(errors)
            for field, errors in errors.items()
        }

    def _format_errors(self, errors):
        if isinstance(errors, (list, tuple)):
            return self._format_first(errors)
        return self._format_one(errors)

    def _format_first(self, errors):
        return self._format_one(errors[0])

    def _format_one(self, error):
        error.pop('_schema', None)
        return error


class InvalidListParamException(APIException, _MarshmallowDetailFormatter):

    def __init__(self, errors):
        super().__init__(status_code=400,
                         message='Invalid data',
                         error_id='invalid_data',
                         resource='plugins',
                         details=self.format_details(errors))


class InvalidInstallParamException(APIException, _MarshmallowDetailFormatter):

    def __init__(self, errors):
        super().__init__(status_code=400,
                         message='Invalid data',
                         error_id='invalid_data',
                         resource='plugins',
                         details=self.format_details(errors))


class InvalidInstallQueryStringException(APIException, _MarshmallowDetailFormatter):

    def __init__(self, errors):
        super().__init__(status_code=400,
                         message='Invalid data',
                         error_id='invalid_data',
                         resource='plugins',
                         details=self.format_details(errors))


class PluginValidationException(Exception, _MarshmallowDetailFormatter):

    error_id = 'validation_error'
    message = 'Validation error'
    details = {}

    def __init__(self, errors):
        self.details = self.format_details(errors)


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


class DependencyAlreadyInstalledException(Exception):
    pass


class MarketNotFoundException(APIException):

    def __init__(self):
        super().__init__(status_code=503,
                         message='Market Service Unavailable',
                         error_id='market_service_unavailable',
                         resource='market',
                         details={})
