from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"


    is_post_bkav_store = fields.Boolean(
        string='Có phát hành hóa đơn bkav', 
        related="store_id.is_post_bkav"
    )
    invoice_date = fields.Date(
        string='Invoice/Bill Date',
        related="account_move.invoice_date"
    )
    invoice_exists_bkav = fields.Boolean(
        string="Đã tồn tại trên BKAV", 
        related="account_move.exists_bkav"
    )
    is_synthetic = fields.Boolean(string='Synthetic', default=False)


    def get_total_point(self):
        total_point = self.total_point
        if self.exists_total_point:
            total_point = 0
        else:
            self.write({"exists_total_point": True})
        return total_point

    
