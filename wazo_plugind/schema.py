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


class PluginInstallSchema(Schema):

    url = fields.String(validate=Length(min=1), required=True)
    method = fields.String(validate=OneOf(['git']), required=True)
    options = fields.Dict(missing=dict, required=False)

    @pre_load
    def ensure_dict(self, data):
        return data or {}
