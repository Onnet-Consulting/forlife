from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _domain_location_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    def _domain_location_dest_id(self):
        if self.env.context.get('default_other_export'):
            return "[('reason_type_id', '=', reason_type_id)]"

    transfer_id = fields.Many2one('stock.transfer')
    reason_type_id = fields.Many2one('forlife.reason.type')
    other_export = fields.Boolean(default=False)
    other_import = fields.Boolean(default=False)
    transfer_stock_inventory_id = fields.Many2one('transfer.stock.inventory')
    location_id = fields.Many2one(
        'stock.location', "Source Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=True,
        domain=_domain_location_id,
        states={'done': [('readonly', True)]})

    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=True,
        domain=_domain_location_dest_id,
        states={'done': [('readonly', True)]})

    def action_back_to_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        if self.other_import or self.other_export:
            self.state = 'cancel'
            for line in self.move_line_ids_without_package:
                line.qty_done = 0
                line.reserved_uom_qty = 0
                line.qty_done = 0
            for line in self.move_ids_without_package:
                line.forecast_availability = 0
                line.quantity_done = 0
            layers = self.env['stock.valuation.layer'].search([('stock_move_id.picking_id', '=', self.id)])
            for layer in layers:
                layer.quantity = 0
                layer.unit_cost = 0
                layer.value = 0
                layer.account_move_id.button_draft()
                layer.account_move_id.button_cancel()
        else:
            self.move_ids._action_cancel()
            self.write({'is_locked': True})
        return True


class StockMove(models.Model):
    _inherit = 'stock.move'

    reason_id = fields.Many2one('stock.location')
    occasion_code_id = fields.Many2one('occasion.code', 'Occasion Code')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for r in self:
            if r.product_id:
                r.reason_id = r.picking_id.location_id.id \
                    if r.picking_id.other_import else r.picking_id.location_dest_id.id