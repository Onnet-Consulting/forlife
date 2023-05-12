# -*- coding: utf-8 -*-


from odoo import api, fields,models
from odoo.osv import expression
from datetime import date, datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_sale_type = fields.Selection(
        [('product', 'Hàng hóa'),
         ('service', 'Dịnh vụ/Tài sản'),
         ('integrated', 'Tích hợp')],
        string='Loại bán hàng', default='product')
    x_sale_chanel = fields.Selection(
        [('pos', 'Đơn bán hàng POS'),
         ('wholesale', 'Đơn bán buôn'),
         ('intercompany', 'Đơn bán hàng liên công ty'),
         ('online', 'Đơn bán hàng online')],
        string='Kênh bán', default='wholesale')
    x_account_analytic_ids = fields.Many2many('account.analytic.account', string='Trung tâm chi phí')
    x_occasion_code_ids = fields.Many2many('occasion.code', string='Mã vụ việc')

    def get_rule_domain(self):
        domain = ['&', ('location_dest_id', '=', self.partner_shipping_id.property_stock_customer.id),
                  ('action', '!=', 'push')]
        if self.env.su and self.company_id:
            domain_company = ['|', ('company_id', '=', False), ('company_id', 'child_of', self.company_id.ids)]
            domain = expression.AND([domain, domain_company])
        return domain

    def get_rule(self):
        if self.warehouse_id:
            domain = expression.AND(
                [['|', ('warehouse_id', '=', self.warehouse_id.id), ('warehouse_id', '=', False)],
                 self.get_rule_domain()])
            warehouse_routes = self.warehouse_id.route_ids
            if warehouse_routes:
                res = self.env['stock.rule'].search(
                    expression.AND([[('route_id', 'in', warehouse_routes.ids)], domain]),
                    order='route_sequence, sequence', limit=1)
            return res

    def action_create_picking(self):
        rule = self.get_rule()
        master = {
            'origin': self.name,
            'company_id': self.company_id.id,
            'move_type': self.picking_policy,
            'partner_id': self.partner_id.id,
            'picking_type_id': rule.picking_type_id.id,
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.partner_shipping_id.property_stock_customer.id,
            'sale_id': self.id
        }
        list_location = []
        stock_move_ids = {}
        stock_move_ids['Null'] = []
        for line in self.order_line:
            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            detail_data = {
                'name': line.name,
                'company_id': line.company_id.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_uom_qty,
                'partner_id': line.order_id.partner_id.id,
                'location_id': line.order_id.warehouse_id.lot_stock_id.id,
                'location_dest_id': line.order_id.partner_shipping_id.property_stock_customer.id,
                'rule_id': rule.id,
                'procure_method': 'make_to_stock',
                'origin': line.order_id.name,
                'picking_type_id': rule.picking_type_id.id,
                'date': datetime.now(),
                'date_deadline': datetime.now(),
                'description_picking': line.name,
                'sale_line_id': line.id,
                'x_scheduled_date': line.x_scheduled_date,
                'group_id': group_id.id
            }
            if line.x_location_id:
                if line.x_location_id.id not in list_location:
                    stock_move_ids[line.x_location_id.id] = [(0, 0, detail_data)]
                    list_location.append(line.x_location_id.id)
                else:
                    stock_move_ids[line.x_location_id.id].append((0, 0, detail_data))
            else:
                stock_move_ids['Null'].append((0, 0, detail_data))
        for move in stock_move_ids:
            master_data = master
            master_data['name'] = rule.picking_type_id.sequence_id.next_by_id()
            picking_id = self.env['stock.picking'].create(master_data)
            picking_id.move_ids_without_package = stock_move_ids[move]
            picking_id.action_confirm()
        self.state = 'sale'

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_cart_discount_fixed_price = fields.Float('Giảm giá cố định', digits=(16, 2))
    x_location_id = fields.Many2one('stock.location', 'Địa điểm kho')
    x_scheduled_date = fields.Date(string='Ngày giao hàng dự kiến')
    x_manufacture_order_code_id = fields.Many2one('forlife.production', string='Mã lệnh sản xuất')
    x_product_code_id = fields.Many2one('product.template', string='Mã tài sản')
    x_account_analytic_id = fields.Many2one('account.analytic.account', string='Trung tâm chi phí')
    x_occasion_code_id = fields.Many2one('occasion.code', string='Mã vụ việc')


    @api.onchange('product_id')
    def _onchange_product_get_domain(self):
        self.x_account_analytic_id = self.order_id.x_account_analytic_ids[0] if self.order_id.x_account_analytic_ids else None
        self.x_occasion_code_id = self.order_id.x_occasion_code_ids[0] if self.order_id.x_occasion_code_ids else None
        if self.order_id.x_sale_type and self.order_id.x_sale_type in ('product', 'service'):
            domain = [('product_type', '=', self.order_id.x_sale_type)]
            return {'domain': {'product_id': [('sale_ok', '=', True), '|', ('company_id', '=', False),
                                              ('company_id', '=', self.order_id.company_id)] + domain}}

    @api.onchange('price_unit', 'discount', 'product_uom_qty')
    def compute_cart_discount_fixed_price(self):
        self.x_cart_discount_fixed_price = self.price_unit * self.discount * self.product_uom_qty / 100

    @api.onchange('price_unit')
    def set_price_unit(self):
        if self.product_id and self.price_unit:
            if self.product_id.product_tmpl_id.x_negative_value:
                self.price_unit = - abs(self.price_unit)
            else:
                self.price_unit = abs(self.price_unit)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        res = super()._compute_amount()
        for line in self:
            line.price_subtotal = line.price_unit * line.product_uom_qty - line.x_cart_discount_fixed_price
        return res
