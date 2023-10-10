from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReasonRefuse(models.TransientModel):
    _name = 'reason.refuse.product'
    _description = 'Reason Resufe for Product Defective'

    name = fields.Text('Lí do', required=True)
    pack_id = fields.Many2one('product.defective.pack', default=lambda self: self.env.context.get('active_id'))
    warehouse_id = fields.Many2one('stock.warehouse', related='pack_id.store_id.warehouse_id')
    is_transferred = fields.Boolean(default=False)
    from_location_id = fields.Many2one(
        'stock.location', domain="[('warehouse_id', '=', warehouse_id)]")
    to_location_id = fields.Many2one('stock.location')

    @api.onchange('is_transferred')
    def onchange_transfer(self):
        if self.is_transferred and self.warehouse_id:
            self.from_location_id = self.warehouse_id.lot_stock_id

    def action_confirm(self):
        active_model = self.env.context.get('active_model', 'product.defective')
        object_id = self.env[active_model].browse(self._context.get('active_id'))
        if object_id.exists() and active_model == 'product.defective.pack':
            line_ids = object_id.line_ids.filtered(
                lambda l: l.selected and l.state not in ('new', 'cancel') and not l.is_transferred)
            if not line_ids:
                raise UserError('Không có dòng nào được chọn để Từ chối !')
            line_ids.reason_refuse_product = self.name
            if self.is_transferred:
                line_ids.write({
                    'from_location_id': self.from_location_id.id,
                    'to_location_id': self.to_location_id.id,
                    'is_transferred': True
                })
            line_ids.selected = False
            line_ids.action_refuse()
        elif object_id.exists() and active_model == 'product.defective':
            object_id.reason_refuse_product = self.name
            object_id.action_refuse()
