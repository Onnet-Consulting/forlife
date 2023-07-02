# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'search.by.name.code']


class Store(models.Model):
    _name = 'store'
    _inherit = ['store', 'search.by.name.code']
