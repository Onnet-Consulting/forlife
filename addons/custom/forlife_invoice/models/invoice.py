from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _domain_purchase_order(self):
        return [('custom_state', '=', 'approved')]

    invoice_description = fields.Char(string="Invoce Description")
    invoice_reference = fields.Char(string="Invoice Reference")
    currency_rate = fields.Float("Currency Rate")
    purchase_type = fields.Selection([
        ('product', 'Goods'),
        ('service', 'Service'),
        ('asset', 'Asset'),
    ], string='PO Type', default='product')
    purchase_order_id = fields.Many2one('purchase.order', string="Auto-Complete")

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        if self.purchase_order_id:
            self.purchase_type = self.purchase_order_id.purchase_type


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    description = fields.Char(string="Description")
    type = fields.Selection(related="product_id.detailed_type")
