from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    request_id = fields.Many2one('purchase.request')
    purchase_request_ids = fields.Many2many('purchase.request')
    partner_id = fields.Many2one('res.partner', required=False)
    production_id = fields.Many2one('forlife.production', string='Production Order')
    event_id = fields.Many2one('forlife.event', string='Event Program')
    has_contract_commerce = fields.Boolean(string='Commerce Contract')
    rejection_reason = fields.Text()
    approval_logs_ids = fields.One2many('approval.logs', 'purchase_order_id')

    def action_approved(self):
        for rec in self:
            for line in rec.order_line:
                if not line.purchase_request_line_id:
                    continue
                purchase_request_line = line.purchase_request_line_id
                purchase_request_name = purchase_request_line.request_id.name
                if (line.product_qty + purchase_request_line.order_quantity) > purchase_request_line.purchase_quantity:
                    raise ValidationError('Số lượng sản phẩm %s còn lại không đủ!\nVui lòng check Purchase Request %s.' % (line.product_id.name, purchase_request_name))
        res = super(PurchaseOrder, self).action_approved()
        for rec in self:
            rec.write({
                'approval_logs_ids': [(0, 0, {
                    'res_model': rec._name,
                    'request_approved_date': date.today(),
                    'approval_user_id': rec.env.user.id,
                    'note': 'Approve',
                    'state': 'approved',
                })],
            })
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    state = fields.Selection(related='order_id.state', store=1)
    purchase_request_line_id = fields.Many2one('purchase.request.line', ondelete='cascade')
