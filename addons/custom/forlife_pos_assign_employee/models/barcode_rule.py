# -*- coding: utf-8 -*-

from odoo import models, fields


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    type = fields.Selection(selection_add=[('employee', 'Nhân viên bán hàng')], ondelete={'employee': 'set default'})

    def get_prefix_by_type(self, type):
        res = self.search([('type', '=', type)], order='sequence', limit=1)
        return (res.pattern or 'NVBH').strip('.')
