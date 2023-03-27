from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transfer_id = fields.Many2one('stock.transfer')
    reason_type_id = fields.Many2one('forlife.reason.type')
    other_export = fields.Boolean(default=False)
    other_import = fields.Boolean(default=False)

    def action_back_to_draft(self):
        self.state = 'draft'


class StockMove(models.Model):
    _inherit = 'stock.move'

    reason_type_id = fields.Many2one('forlife.reason.type')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for r in self:
            if r.product_id:
                r.reason_type_id = r.picking_id.reason_type_id.id
