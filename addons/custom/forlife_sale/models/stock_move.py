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