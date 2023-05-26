from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # @api.model
    # def create(self, vals):
    #     res = super().create(vals)
    #     if not res.purchase_order_product_id or res.purchase_order_product_id[0].is_inter_company != False \
    #             or res.purchase_order_product_id[0].type_po_cost != 'cost':
    #         return res
    #     for line in res.invoice_line_ids:
    #         if line.product_id:
    #             line._compute_account_id()
    #     return res

