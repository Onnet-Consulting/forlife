from odoo import api, fields, models, _


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.model
    def get_order_line(self, order_id):
        lst_line = []
        if order_id:
            pos_line_ids = self.search([('order_id', '=', order_id), ('is_promotion', '=', False)])
            for line in pos_line_ids:
                lst_line.append({
                    'id': line.id,
                    'barcode': line.product_id.barcode if line.product_id.barcode else '',
                    'display_name': line.product_id.display_name,
                    'quantity': line.qty,
                    'original_price':line.original_price,
                    'money_is_reduced': line.money_is_reduced
                })
        return lst_line