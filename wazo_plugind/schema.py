# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from marshmallow import EXCLUDE, pre_load
from xivo.mallow import fields
from xivo.mallow_helpers import Schema
from xivo.mallow.validate import OneOf
from xivo.mallow.validate import Length
from xivo.mallow.validate import Range
from xivo.mallow.validate import Regexp
from .config import _MAX_PLUGIN_FORMAT_VERSION

_DEFAULT_PLUGIN_FORMAT_VERSION = 0
_PLUGIN_NAME_REGEXP = r'^[a-z0-9-]+$'
_PLUGIN_NAMESPACE_REGEXP = r'^[a-z0-9]+$'


class DependencyMetadataSchema(Schema):

    namespace = fields.String(validate=Length(min=1), required=True)
    name = fields.String(validate=Length(min=1), required=True)


class GitInstallOptionsSchema(Schema):

    ref = fields.String(missing='master', validate=Length(min=1))
    url = fields.String(validate=Length(min=1), required=True)


class MarketInstallOptionsSchema(Schema):

    namespace = fields.String(validate=Length(min=1), required=True)
    name = fields.String(validate=Length(min=1), required=True)
    version = fields.String()


class MarketListRequestSchema(Schema):

    direction = fields.String(validate=OneOf(['asc', 'desc']), missing='asc')
    order = fields.String(validate=Length(min=1), missing='name')
    limit = fields.Integer(validate=Range(min=0), missing=None)
    offset = fields.Integer(validate=Range(min=0), missing=0)
    search = fields.String(missing=None)
    installed = fields.Boolean()


class MarketVersionResultSchema(Schema):

    upgradable = fields.Boolean(required=True)
    version = fields.String(required=True)
    min_wazo_version = fields.String()
    max_wazo_version = fields.String()


class PluginMetadataSchema(Schema):

    version_fields = ['version', 'max_wazo_version', 'min_wazo_version']
    current_version = None

    name = fields.String(validate=Regexp(_PLUGIN_NAME_REGEXP), required=True)
    namespace = fields.String(validate=Regexp(_PLUGIN_NAMESPACE_REGEXP), required=True)
    version = fields.String(required=True)
    plugin_format_version = fields.Integer(validate=Range(min=0,
                                                          max=_MAX_PLUGIN_FORMAT_VERSION),
                                           missing=_DEFAULT_PLUGIN_FORMAT_VERSION)
    max_wazo_version = fields.String()
    min_wazo_version = fields.String()
    depends = fields.Nested(MarketInstallOptionsSchema, many=True,
                            unknown=EXCLUDE)

    @pre_load
    def ensure_string_versions(self, data):
        for field in self.version_fields:
            if field not in data:
                continue
            value = data[field]
            if not isinstance(value, (float, int)):
                continue
            data[field] = str(value)
        return data

    def on_bind_field(self, field_name, field_obj):
        if field_name == 'max_wazo_version':
            self._set_max_wazo_version_parameters(field_obj)
        elif field_name == 'min_wazo_version':
            self._set_min_wazo_version_parameters(field_obj)

    def _set_max_wazo_version_parameters(self, field_obj):
        field_obj.validators = [Range(min=self.current_version)]

    def _set_min_wazo_version_parameters(self, field_obj):
        field_obj.validators = [Range(max=self.current_version)]


class MarketListResultSchema(Schema):

    homepage = fields.String()
    color = fields.String()
    display_name = fields.String()
    name = fields.String(validate=Regexp(_PLUGIN_NAME_REGEXP), required=True)
    namespace = fields.String(validate=Regexp(_PLUGIN_NAMESPACE_REGEXP), required=True)
    tags = fields.List(fields.String)
    author = fields.String()
    versions = fields.Nested(MarketVersionResultSchema, many=True,
                             required=True, unknown=EXCLUDE)
    screenshots = fields.List(fields.String)
    icon = fields.String()
    description = fields.String()
    short_description = fields.String()
    license = fields.String()
    installed_version = fields.String(missing=None)


class OptionField(fields.Field):

    _options = {
        'git': fields.Nested(GitInstallOptionsSchema, unknown=EXCLUDE),
        'market': fields.Nested(MarketInstallOptionsSchema, unknown=EXCLUDE),
    }

    def _deserialize(self, value, attr, data):
        method = data.get('method')
        concrete_options = self._options.get(method)
        if not concrete_options:
            return {}
        return concrete_options._deserialize(value, attr, data)


class PluginInstallSchema(Schema):

    method = fields.String(validate=OneOf(['git', 'market']), required=True)
    options = OptionField(missing=dict, required=True)


class PluginInstallQueryStringSchema(Schema):

    reinstall = fields.Boolean(default=False, missing=False)
