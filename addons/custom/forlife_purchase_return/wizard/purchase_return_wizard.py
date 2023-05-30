from odoo import fields, models, api, _


class PurchaseReturnWizard(models.TransientModel):
    _name = "purchase.return.wizard"
    _description = "Purchase Return Wizard"
