from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    exists_total_point = fields.Boolean(default=False, copy=False, string="Exists total point")

    is_post_bkav_store = fields.Boolean(
        string='Có phát hành hóa đơn bkav', 
        related="store_id.is_post_bkav"
    )


    def get_total_point(self):
        total_point = self.total_point
        if self.exists_total_point:
            total_point = 0
        else:
            self.write({"exists_total_point": True})
        return total_point

    
