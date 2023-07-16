# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_need_scan_barcode = fields.Boolean(compute='_compute_need_scan_barcode', compute_sudo=True, store=True)

    @api.depends('product_id', 'product_id.is_need_scan_barcode')
    def _compute_need_scan_barcode(self):
        for rec in self:
            rec.is_need_scan_barcode = rec.product_id.is_need_scan_barcode

    def write(self, vals):
        for item in self:
            if not item.picking_id.date_done:
                continue
            vals['date'] = item.picking_id.date_done
        return super().write(vals)
