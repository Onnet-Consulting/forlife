from odoo import api, fields, models
from ast import literal_eval


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    point_addition = fields.Integer('Point(+)', compute='_compute_value_follow_program_event', store=True)
    point_addition_event = fields.Integer('Point (+) Event', compute='_compute_value_follow_program_event', store=True)
    point = fields.Integer('Points Used', readonly=True)
    money_is_reduced = fields.Monetary('Money is reduced', compute='_compute_money_is_reduced_line')
    discount_details_lines = fields.One2many('pos.order.line.discount.details', 'pos_order_line_id', 'Discount details')
    is_new_line_point = fields.Boolean()

    @api.depends('discount_details_lines.money_reduced')
    def _compute_money_is_reduced_line(self):
        for rec in self:
            rec.money_is_reduced = sum([dis.money_reduced for dis in rec.discount_details_lines])

    @api.model_create_multi
    def create(self, vals_list):
        for idx, line in enumerate(vals_list):
            if 'point' in line and line['point']:
                vals_list[idx]['discount_details_lines'] = line.get('discount_details_lines', []) + [
                    (0, 0, {
                        'type': 'point',
                        'listed_price': line['original_price'],
                        'recipe': -line['point']/1000,
                    })
                ]
            if 'money_reduce_from_product_defective' in line and line['money_reduce_from_product_defective']:
                vals_list[idx]['discount_details_lines'] = line.get('discount_details_lines', []) + [
                    (0, 0, {
                        'type': 'product_defective',
                        'recipe': line['money_reduce_from_product_defective'],
                        'listed_price': line['original_price']
                    })
                ]
            if 'discount' in line and line['discount']:
                vals_list[idx]['discount_details_lines'] = line.get('discount_details_lines', []) + [
                    (0, 0, {
                        'type': 'handle',
                        'recipe': (line['discount']*line['qty']*line['original_price'])/100,
                        'listed_price': line['original_price']
                    })
                ]
        return super(PosOrderLine, self).create(vals_list)

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['point'] = orderline.point
        result['is_new_line_point'] = orderline.is_new_line_point
        return result

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
                # compute c
                # is_purchased_of_format, is_purchased_of_forlife = rec.order_id.partner_id._check_is_purchased()
                if not rec.order_id.is_refund_order and not rec.order_id.is_change_order:
                    if dict_products_points:
                        for key, val in dict_products_points.items():
                            if rec.product_id in key:
                                if rec.order_id.partner_id.is_purchased_of_forlife and branch_id == brand_tokyolife:
                                    rec.point_addition = int(dict_products_points[key]) * rec.qty
                                elif rec.order_id.partner_id.is_purchased_of_format and branch_id == brand_format:
                                    rec.point_addition = int(dict_products_points[key]) * rec.qty
                                else:
                                    rec.point_addition = int(dict_products_points[key]) * rec.order_id.program_store_point_id.first_order * rec.qty
                                break
                            else:
                                rec.point_addition = 0
                    else:
                        rec.point_addition = 0
                    # compute d
                    if product_ids_valid_event:
                        for key, val in product_ids_valid_event.items():
                            if rec.product_id in key:
                                rec.point_addition_event = int(product_ids_valid_event[key]) * rec.qty
                                break
                            else:
                                rec.point_addition_event = 0
                    else:
                        rec.point_addition_event = 0
                else:
                    if dict_products_points:
                        for key, val in dict_products_points.items():
                            if rec.product_id in key and rec.price_subtotal_incl > 0 and rec.product_id.is_product_auto is False:
                                if rec.order_id.partner_id.is_purchased_of_forlife and branch_id == brand_tokyolife:
                                    rec.point_addition = int(dict_products_points[key]) * rec.qty
                                elif rec.order_id.partner_id.is_purchased_of_format and branch_id == brand_format:
                                    rec.point_addition = int(dict_products_points[key]) * rec.qty
                                else:
                                    rec.point_addition = int(dict_products_points[key]) * rec.order_id.program_store_point_id.first_order * rec.qty
                                break
                            else:
                                rec.point_addition = 0
                    else:
                        rec.point_addition = 0
                    #####
                    if product_ids_valid_event:
                        for key, val in product_ids_valid_event.items():
                            if rec.product_id in key and rec.price_subtotal_incl > 0 and rec.product_id.is_product_auto is False:
                                rec.point_addition_event = int(product_ids_valid_event[key]) * rec.qty
                                break
                            else:
                                rec.point_addition_event = 0
                    else:
                        rec.point_addition_event = 0

    def _prepare_dict_point_product_program(self):
        if self.order_id.program_store_point_id:
            program_point_products = self.order_id.program_store_point_id.points_product_ids.filtered(
                lambda x: x.state == 'effective' and x.from_date < self.order_id.date_order < x.to_date)
            dict_product_poit_add = {}
            for r in program_point_products:
                dict_product_poit_add[r.product_ids] = r.point_addition
            return dict_product_poit_add
        return False

    def _prepare_dict_point_product_event(self):
        event_valid = self.order_id.get_event_match(self.order_id)
        dict_product_poit_add = {}
        if event_valid:
            domain = [('id','in',[x.partner_id.id for x in self.env['contact.event.follow'].sudo().search([('event_id','=',event_valid.id)])])]
            partner_condition = self.env['res.partner'].search(domain)
            if self.order_id.partner_id.id in partner_condition.ids or not partner_condition:
                for r in event_valid.points_product_ids.filtered(lambda x: x.state == 'effective'):
                    dict_product_poit_add[r.points_product_id.product_ids] = r.point_addition
                return dict_product_poit_add
            else:
                return False
        else:
            return False
