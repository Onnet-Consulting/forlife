from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    point_addition = fields.Integer('Point(+)', compute='_compute_value_follow_program_event', store=True)
    point_addition_event = fields.Integer('Point (+) Event', compute='_compute_value_follow_program_event', store=True)

    @api.depends('order_id.program_store_point_id')
    def _compute_value_follow_program_event(self):
        brand_format = self.env.ref('forlife_point_of_sale.brand_format', raise_if_not_found=False).id
        brand_tokyolife = self.env.ref('forlife_point_of_sale.brand_tokyolife', raise_if_not_found=False).id
        for rec in self:
            if not rec.order_id.partner_id:
                rec.point_addition = 0
                rec.point_addition_event = 0
            else:
                branch_id = rec.order_id.program_store_point_id.brand_id.id
                dict_products_points = rec._prepare_dict_point_product_program()
                product_ids_valid_event = rec._prepare_dict_point_product_event()
                #compute c
                # is_purchased_of_format, is_purchased_of_forlife = rec.order_id.partner_id._check_is_purchased()

                if dict_products_points:
                    for key, val in dict_products_points.items():
                        if rec.product_id in key:
                            if rec.order_id.partner_id.is_purchased_of_forlife and branch_id == brand_tokyolife:
                                rec.point_addition = int(dict_products_points[key])*rec.qty
                            elif rec.order_id.partner_id.is_purchased_of_format and branch_id == brand_format:
                                rec.point_addition = int(dict_products_points[key])*rec.qty
                            else:
                                rec.point_addition = int(dict_products_points[key])*rec.order_id.program_store_point_id.first_order*rec.qty
                            break
                        else:
                            rec.point_addition = 0
                else:
                    rec.point_addition = 0
                #compute d
                if product_ids_valid_event:
                    for key, val in product_ids_valid_event.items():
                        if rec.product_id in key:
                            rec.point_addition_event = int(product_ids_valid_event[key])*rec.qty
                            break
                        else:
                            rec.point_addition_event = 0
                else:
                    rec.point_addition_event = 0

    def _prepare_dict_point_product_program(self):
        if self.order_id.program_store_point_id:
            program_point_products = self.order_id.program_store_point_id.points_product_ids.filtered(lambda x: x.state == 'effective' and x.from_date < self.order_id.date_order < x.to_date)
            dict_product_poit_add = {}
            for r in program_point_products:
                dict_product_poit_add[r.product_ids] = r.point_addition
            return dict_product_poit_add
        return False

    def _prepare_dict_point_product_event(self):
        event_valid = self.order_id.get_event_match(self.order_id)
        dict_product_poit_add = {}
        if event_valid:
            for r in event_valid.points_product_ids.filtered(lambda x: x.state == 'effective'):
                dict_product_poit_add[r.points_product_id.product_ids] = r.point_addition
            return dict_product_poit_add
        else:
            return False




