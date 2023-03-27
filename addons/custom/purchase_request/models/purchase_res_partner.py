from odoo import api, fields, models, _

class PurchaseResPartner(models.Model):
    _inherit = 'res.partner'

    def name_get(self):
        return [(item.id, item.code or item.name) if item.active and item.code else (item.id, item.name) for item in
                self] if self.env.context.get('form') == 'purchase_request_from_view' else super(PurchaseResPartner,self).name_get()
