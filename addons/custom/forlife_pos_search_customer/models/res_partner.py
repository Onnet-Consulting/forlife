from odoo import models, api, fields, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _generate_order_by(self, order_spec, query):
        if self.env.context.get('ignore_order_by', False):
            return ''
        return super(ResPartner, self)._generate_order_by(order_spec, query)
