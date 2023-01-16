from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    point_addition = fields.Integer('Point(+)')
    point_event = fields.Integer('Point (+) Event')

    @api.depends('order_id.program_store_point_id')
    def _compute_value_follow_event(self):
        pass
        # event_valid = self.order_id.get_event_match(self.order_id)
        # points_product_ids = self.order_id.program_store_point_id.points_product_ids
        # dict_product_poit_add = {}
        # point_products = event_valid.points_product_ids.filtered(lambda x: x.state == 'effective')
        # for r in point_products:
        #     dict_product_poit_add[r.points_product_id.product_ids] = r.point_addition
        # # product_ids = [y for x in product for y in x]
        # print(dict_product_poit_add)
        # for rec in self:
        #     for key, val in dict_product_poit_add.items():
        #         if rec.product_id in key:
        #             rec.point_addition = int(dict_product_poit_add[key])
        #             break
        #         else:
        #             rec.point_addition = 0


