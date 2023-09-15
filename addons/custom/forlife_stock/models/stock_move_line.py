# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    po_id = fields.Char('')
    ref_asset = fields.Many2one('assets.assets', 'Thẻ tài sản')
    occasion_code_id = fields.Many2one('occasion.code', 'Occasion Code')
    work_production = fields.Many2one('forlife.production', string='Lệnh sản xuất', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")
    sequence = fields.Integer(string="STT dòng")

    def write(self, vals):
        for item in self:
            if not item.picking_id.date_done:
                continue
            vals['date'] = item.picking_id.date_done
        return super().write(vals)
