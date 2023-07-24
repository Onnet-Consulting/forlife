from odoo import api, fields, models, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    def approve_company_sale(self, company_sale):
        sale, invoice, picking = super(PurchaseOrder, self).approve_company_sale(company_sale)
        for line in invoice:
            line.write(
                {
                    "po_source_id": self.id
                }
            )
        return sale, invoice, picking