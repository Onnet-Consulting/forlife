# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AttributeCodeConfig(models.Model):
    _name = 'attribute.code.config'
    _description = 'Attribute Code Config'

    attr_code = fields.Char('Attribute Code')
