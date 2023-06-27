from odoo import api, fields, models, _

class PurchaseResPartner(models.Model):
    _inherit = 'res.partner'

    def name_get(self):
        return [(item.id, f"[{item.code}] {item.name}") if item.active and item.code else (item.id, item.name) for item in
                self] if self.env.context.get('form') == 'purchase_request_from_view' else super(PurchaseResPartner,self).name_get()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        domain = []
        if self.env.context.get('res_partner_search_mode') == 'supplier':
            args = list(args or [])
            if name:
                domain += ['|', ('name', operator, name), ('code', operator, name)]
        return super(PurchaseResPartner, self).name_search(name, domain + args, operator=operator, limit=limit)
