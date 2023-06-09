from odoo import api, fields, models, _

class ReasonRefuse(models.TransientModel):
    _name = 'reason.refuse.product'
    _description = 'Reason Resufe for Product Defective'

    name = fields.Text('Lí do')

    def action_confirm(self):
        product_defective = self.env['product.defective'].browse(self._context.get('active_id'))
        product_defective.action_refuse()
