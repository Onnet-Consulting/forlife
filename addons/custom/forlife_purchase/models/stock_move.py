# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_pk_purchase = fields.Boolean(string="Là phiếu của Po", default=False)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    purchase_uom = fields.Many2one('uom.uom', string="Đơn vị mua")
    quantity_change = fields.Float(string="Số lượng quy đổi")
    quantity_purchase_done = fields.Float(string="Số lượng mua hoàn thành")

    @api.onchange('quantity_change', 'quantity_purchase_done')
    def onchange_quantity_purchase_done(self):
        self.qty_done = self.quantity_purchase_done * self.quantity_change


class StockMove(models.Model):
    _inherit = 'stock.move'