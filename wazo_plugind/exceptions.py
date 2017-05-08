# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xivo.rest_api_helpers import APIException


class UnsupportedDownloadMethod(APIException):

    def __init__(self):
        super().__init__(status_code=501,
                         message='Unsupported download method',
                         error_id='unsupported_download_method',
                         details={})


class InvalidMetadata(Exception):
    pass


class InvalidNamespaceException(InvalidMetadata):
    pass


class InvalidNameException(InvalidMetadata):
    pass


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
