# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from marshmallow import fields, Schema, validate, pre_load


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

        return {
            'constraint_id': self.constraint_id,
            'constraint': [self.min, self.max],
            'message': msg,
        }


class GitInstallOptionsSchema(Schema):

    ref = fields.String(missing='master', validate=Length(min=1), required=False)


class MarketListRequestSchema(Schema):

    direction = fields.String(validate=OneOf(['asc', 'desc']), missing='asc')
    order = fields.String(validate=Length(min=1), missing='name')
    limit = fields.Integer(validate=Range(min=0), missing=None)
    offset = fields.Integer(validate=Range(min=0), missing=0)
    search = fields.String(missing=None)

    @pre_load
    def ensure_dict(self, data):
        return data or {}


class PluginInstallSchema(Schema):

    url = fields.String(validate=Length(min=1), required=True)
    method = fields.String(validate=OneOf(['git']), required=True)
    options = fields.Nested(GitInstallOptionsSchema, missing=dict, required=False)

    @pre_load
    def ensure_dict(self, data):
        return data or {}
