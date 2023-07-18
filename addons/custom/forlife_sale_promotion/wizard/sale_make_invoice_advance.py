# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from datetime import date, datetime


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        res = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)
        if res and sale_orders.promotion_ids:
            res.write({
                'promotion_ids': [(0, 0, {
                    "product_id": prm.product_id.id,
                    "value": prm.value,
                    "promotion_type": prm.promotion_type,
                    "account_id": prm.account_id.id,
                    "analytic_account_id": prm.analytic_account_id.id,
                    "description": prm.description,
                    "move_id": res.id
                }) for prm in sale_orders.promotion_ids]
            })

        return res

    # def update_stock_move(self):
    #     rule = self.get_rule()
    #     list_location = []
    #     stock_move_ids = {}
    #     line_x_scheduled_date = []
    #     for line in self.order_line:
    #         date = datetime.combine(line.x_scheduled_date,
    #                                 datetime.min.time()) if line.x_scheduled_date else datetime.now()
    #         group_id = line._get_procurement_group()
    #         if not group_id:
    #             group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
    #             line.order_id.procurement_group_id = group_id
    #         detail_data = {
    #             'name': line.name,
    #             'company_id': line.company_id.id,
    #             'product_id': line.product_id.id,
    #             'product_uom': line.product_uom.id,
    #             'product_uom_qty': line.product_uom_qty,
    #             'partner_id': line.order_id.partner_id.id,
    #             'location_id': line.x_location_id.id,
    #             'location_dest_id': line.order_id.partner_shipping_id.property_stock_customer.id,
    #             'rule_id': rule.id,
    #             'procure_method': 'make_to_stock',
    #             'origin': line.order_id.name,
    #             'picking_type_id': rule.picking_type_id.id,
    #             'date_deadline': datetime.now(),
    #             'description_picking': line.name,
    #             'sale_line_id': line.id,
    #             'occasion_code_id': line.x_occasion_code_id,
    #             'work_production': line.x_manufacture_order_code_id,
    #             'account_analytic_id': line.x_account_analytic_id,
    #             'group_id': group_id.id
    #         }
    #         line_x_scheduled_date.append((line.id, str(date)))
    #         if line.x_location_id:
    #             if line.x_location_id.id not in list_location:
    #                 stock_move_ids[line.x_location_id.id] = [(0, 0, detail_data)]
    #                 list_location.append(line.x_location_id.id)
    #             else:
    #                 stock_move_ids[line.x_location_id.id].append((0, 0, detail_data))
    #     if self.x_process_punish or self.x_shipping_punish:
    #         condition = True
    #     else:
    #         condition = False
    #     for move in stock_move_ids:
    #         move_ids_without_package
    #         picking_id.move_ids_without_package = stock_move_ids[move]
    #         sql = f"""
    #             with A as (
    #                 SELECT *
    #                 FROM ( VALUES {str(line_x_scheduled_date).replace('[', '').replace(']', '')})as A(sale_line_id,date)
    #                 )
    #             update stock_move
    #                 set date = A.date::timestamp
    #             from A
    #             where stock_move.sale_line_id = A.sale_line_id
    #             """
    #         self._cr.execute(sql)

