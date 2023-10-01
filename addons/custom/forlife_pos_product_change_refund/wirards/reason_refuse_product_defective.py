from odoo import api, fields, models, _


class ReasonRefuse(models.TransientModel):
    _name = 'reason.refuse.product'
    _description = 'Reason Resufe for Product Defective'

    name = fields.Text('Lí do', required=True)

    def action_confirm(self):
        active_model = self.env.context.get('active_model', 'product.defective')
        object_id = self.env[active_model].browse(self._context.get('active_id'))
        if object_id.exists() and active_model == 'product.defective.pack':
            object_id.line_ids.filtered(lambda l: l.selected).reason_refuse_product = self.name
            object_id.action_refuse()
        elif object_id.exists() and active_model == 'product.defective':
            object_id.reason_refuse_product = self.name
            object_id.action_refuse()
