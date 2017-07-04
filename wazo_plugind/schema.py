# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import fields, Schema, validate, pre_load
from .config import _MAX_PLUGIN_FORMAT_VERSION

_DEFAULT_PLUGIN_FORMAT_VERSION = 0


fields.String.default_error_messages = {
    'required': {'message': 'Missing data for required field.',
                 'constraint_id': 'required',
                 'constraint': 'required'},
    'invalid': {'message': 'Not a valid string.',
                'constraint_id': 'type',
                'constraint': 'string'},
    'null': {'message': 'Field may not be null.',
             'constraint_id': 'not_null',
             'constraint': 'not_null'},
}


class Length(validate.Length):

    constraint_id = 'length'

    def _format_error(self, value, message):
        msg = super()._format_error(value, message)

        return {
            'constraint_id': self.constraint_id,
            'constraint': {'min': self.min, 'max': self.max},
            'message': msg,
        }


class OneOf(validate.OneOf):

    constraint_id = 'enum'

    def _format_error(self, value):
        msg = super()._format_error(value)

        return {
            'constraint_id': self.constraint_id,
            'constraint': {'choices': self.choices},
            'message': msg,
        }


class Range(validate.Range):

    constraint_id = 'range'

    def _format_error(self, value, *args):
        msg = super()._format_error(value, *args)
        constraint = {}
        if self.min is not None:
            constraint['min'] = self.min
        if self.max is not None:
            constraint['max'] = self.max

        return {
            'constraint_id': self.constraint_id,
            'constraint': constraint,
            'message': msg,
        }


class Regexp(validate.Regexp):

    constraint_id = 'regex'

    def _format_error(self, value):
        msg = super()._format_error(value)

        return {
            'constraint_id': self.constraint_id,
            'constraint': self.regex.pattern,
            'message': msg,
        }


def new_plugin_metadata_schema(current_version):
    class PluginMetadataSchema(Schema):

        version_fields = ['version', 'max_wazo_version', 'min_wazo_version']

        name = fields.String(validate=Regexp(r'^[a-z0-9-]+$'), required=True)
        namespace = fields.String(validate=Regexp(r'^[a-z0-9]+$'), required=True)
        version = fields.String(required=True)
        plugin_format_version = fields.Integer(validate=Range(min=0,
                                                              max=_MAX_PLUGIN_FORMAT_VERSION),
                                               missing=_DEFAULT_PLUGIN_FORMAT_VERSION)
        max_wazo_version = fields.String(validate=Range(min=current_version))
        min_wazo_version = fields.String(validate=Range(max=current_version))

        @pre_load
        def ensure_string_versions(self, data):
            for field in self.version_fields:
                if field not in data:
                    continue
                value = data[field]
                if not isinstance(value, (float, int)):
                    continue
                data[field] = str(value)

    return PluginMetadataSchema()


class GitInstallOptionsSchema(Schema):

    ref = fields.String(missing='master', validate=Length(min=1), required=False)


class MarketInstallOptionsSchema(Schema):

    namespace = fields.String(validate=Length(min=1), required=True)
    name = fields.String(validate=Length(min=1), required=True)
    version = fields.String(required=False)


class MarketListRequestSchema(Schema):

    direction = fields.String(validate=OneOf(['asc', 'desc']), missing='asc')
    order = fields.String(validate=Length(min=1), missing='name')
    limit = fields.Integer(validate=Range(min=0), missing=None)
    offset = fields.Integer(validate=Range(min=0), missing=0)
    search = fields.String(missing=None)

    @pre_load
    def ensure_dict(self, data):
        return data or {}


class OptionField(fields.Nested):

    _options = {
        'git': fields.Nested(GitInstallOptionsSchema, missing=dict, required=False),
        'market': fields.Nested(MarketInstallOptionsSchema, required=True),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(Schema, *args, **kwargs)

    def _deserialize(self, value, attr, data):
        method = data.get('method')
        concrete_options = self._options.get(method)
        if not concrete_options:
            return {}
        return concrete_options._deserialize(value, attr, method)


class PluginInstallSchema(Schema):

    url = fields.String(validate=Length(min=1), required=True)
    method = fields.String(validate=OneOf(['git', 'market']), required=True)
    options = OptionField(missing=dict, required=True)

    @pre_load
    def ensure_dict(self, data):
        return data or {}
