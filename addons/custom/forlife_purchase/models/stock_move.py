# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_pk_purchase = fields.Boolean(string="Là phiếu của Po", default=False)
    picking_xk_id = fields.Many2one('stock.picking', index=True, copy=False)
    account_xk_id = fields.Many2one('account.move', copy=False)

    def view_xk_picking(self):
        # context = { 'create': True, 'delete': True, 'edit': True}
        return {
            'name': _('Forlife Stock Exchange'),
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.picking_xk_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            # 'context': context
        }

    def view_xk_account(self):
        # context = { 'create': True, 'delete': True, 'edit': True}
        account_ids = self.account_xk_id.ids if self.account_xk_id else []
        # stock_valuation_account = self.move_ids.mapped('stock_valuation_layer_ids').mapped('account_move_id')
        # account_ids += stock_valuation_account.ids
        domain = [('id', 'in', account_ids)]
        return {
            'name': _('Forlife Account'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'res_id': self.picking_xk_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            # 'context': context
        }

    def action_cancel(self):
        for rec in self:
            if rec.picking_xk_id:
                rec.picking_xk_id.action_cancel()
                rec.picking_xk_id.action_back_to_draft()
                rec.picking_xk_id.unlink()
            if rec.account_xk_id:
                rec.account_xk_id.button_draft()
                rec.account_xk_id.button_cancel()
        return super(StockPicking, self).action_cancel()

    def action_back_to_draft(self):
        for rec in self:
            if rec.picking_xk_id:
                rec.picking_xk_id.action_cancel()
                rec.picking_xk_id.action_back_to_draft()
                rec.picking_xk_id.unlink()
            if rec.account_xk_id:
                rec.account_xk_id.button_draft()
                rec.account_xk_id.button_cancel()
                rec.account_xk_id.unlink()
        return super(StockPicking, self).action_back_to_draft()


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _domain_reason_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    free_good = fields.Boolean(string="Hàng tặng")
    purchase_uom = fields.Many2one('uom.uom', string="Đơn vị mua")
    quantity_change = fields.Float(string="Số lượng quy đổi")
    quantity_purchase_done = fields.Float(string="Số lượng mua hoàn thành")
    occasion_code_id = fields.Many2one('occasion.code', 'Occasion Code')
    work_production = fields.Many2one('forlife.production', string='Lệnh sản xuất',
                                      domain=[('state', '=', 'approved'), ('status', '=', 'in_approved')])
    account_analytic_id = fields.Many2one('account.analytic.account', string="Cost Center")
    reason_id = fields.Many2one('stock.location', domain=_domain_reason_id)
    is_production_order = fields.Boolean(default=False, compute='compute_production_order')
    is_amount_total = fields.Boolean(default=False, compute='compute_production_order')

    @api.depends('reason_id')
    def compute_production_order(self):
        for rec in self:
            rec.is_production_order = rec.reason_id.is_work_order
            rec.is_amount_total = rec.reason_id.is_price_unit

    @api.onchange('quantity_change', 'quantity_purchase_done')
    def onchange_quantity_purchase_done(self):
        self.qty_done = self.quantity_purchase_done * self.quantity_change


class StockMove(models.Model):
    _inherit = 'stock.move'

    free_good = fields.Boolean(string="Hàng tặng")
    quantity_change = fields.Float(string="Số lượng quy đổi")
    quantity_purchase_done = fields.Float(string="Số lượng mua hoàn thành")
