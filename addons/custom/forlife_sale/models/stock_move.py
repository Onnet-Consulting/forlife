from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _account_entry_move(self, qty, description, svl_id, cost):
        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        for r in res:
            r.update({'narration': self.picking_id.note})
        return res
    def check_quantity(self):
        sql = f"""
            select sq.quantity from stock_quant sq 
                where sq.product_id = {self.product_id.id}
                and sq.location_id = {self.location_id.id}
        """
        self._cr.execute(sql)
        result = self._cr.fetchall()
        if not result or self.product_uom_qty > result[0][0]:
            raise ValidationError(_('Sản phẩm không đủ tồn kho!'))


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        res = super()._get_stock_move_values(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values)
        res['work_to'] = values.get('x_manufacture_order_code_id', False)
        res['occasion_code_id'] = values.get('x_occasion_code_id', False)
        res['account_analytic_id'] = values.get('x_account_analytic_id', False)
        res['ref_asset'] = values.get('x_product_code_id', False)
        res['free_good'] = values.get('free_good', False)
        return res