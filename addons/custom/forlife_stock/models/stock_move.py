# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_confirm(self, merge=True, merge_into=False):
        moves = super(StockMove, self)._action_confirm(merge=False, merge_into=merge_into)
        moves._create_quality_checks()
        return moves

    def _domain_reason_id(self):
        if self.env.context.get('default_other_import'):
            return "[('reason_type_id', '=', reason_type_id)]"

    ref_asset = fields.Many2one('assets.assets', 'Thẻ tài sản')
    name = fields.Char('Description', required=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, index=True, required=False)
    product_uom_qty = fields.Float(
        'Demand',
        digits='Product Unit of Measure',
        default=1.0, required=False, states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")
    product_uom = fields.Many2one(
        'uom.uom', "UoM", required=False, domain="[('category_id', '=', product_uom_category_id)]",
        compute="_compute_product_uom", store=True, readonly=False, precompute=True,
    )
    procure_method = fields.Selection([
        ('make_to_stock', 'Default: Take From Stock'),
        ('make_to_order', 'Advanced: Apply Procurement Rules')], string='Supply Method',
        default='make_to_stock', required=False, copy=False,
        help="By default, the system will take from the stock in the source location and passively wait for availability. "
             "The other possibility allows you to directly create a procurement on the source location (and thus ignore "
             "its current stock) to gather products. If we want to chain moves and have this one to wait for the previous, "
             "this second option should be chosen.")
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True, required=False,
        states={'done': [('readonly', True)]})
    uom_id = fields.Many2one(related="product_id.uom_id", string='Đơn vị')
    amount_total = fields.Float(string='Tổng tiền')
    reason_type_id = fields.Many2one('forlife.reason.type', string='Loại lý do')
    reason_id = fields.Many2one('stock.location', domain=_domain_reason_id)
    occasion_code_id = fields.Many2one('occasion.code', 'Mã vụ việc')
    work_production = fields.Many2one('forlife.production', string='Lệnh sản xuất', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Trung tâm chi phí")
    is_production_order = fields.Boolean(default=False, compute='compute_production_order')
    is_amount_total = fields.Boolean(default=False, compute='compute_production_order')
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        auto_join=True, index=True, required=False,
        check_company=True,
        help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        auto_join=True, index=True, required=False,
        check_company=True,
        help="Location where the system will stock the finished products.")
    date = fields.Datetime(
        'Date Scheduled', default=fields.Datetime.now, index=True, required=False,
        help="Scheduled date until move is done, then date of actual move processing")
    product_other_id = fields.Many2one('forlife.other.in.out.request.line')
    previous_qty = fields.Float(compute='compute_previous_qty', store=1)

    # Lệnh sản xuất, xử lý khi tạo điều chuyển cho LSX A sang LSX B
    work_from = fields.Many2one('forlife.production', string="LSX From", ondelete='restrict')
    work_to = fields.Many2one('forlife.production', string="LSX To", ondelete='restrict')

    @api.depends('reason_id')
    def compute_production_order(self):
        for rec in self:
            rec.is_production_order = rec.reason_id.is_work_order
            rec.is_amount_total = rec.reason_id.is_price_unit

    @api.depends('product_id')
    def compute_product_id(self):
        for rec in self:
            if not rec.reason_id.is_price_unit:
                rec.amount_total = rec.product_id.standard_price
            rec.name = rec.product_id.name

    @api.depends('product_uom_qty', 'picking_id.state')
    def compute_previous_qty(self):
        for rec in self:
            if rec.picking_id.backorder_id:
                back_order = self.env['stock.picking'].search([('id', '=', rec.picking_id.backorder_id.id)])
                if back_order:
                    for r in back_order.move_ids_without_package:
                        if r.product_id == rec.product_id and r.amount_total == rec.amount_total:
                            rec.write({'previous_qty': r.previous_qty})
            else:
                if rec.picking_id.state != 'done':
                    rec.previous_qty = rec.product_uom_qty

    @api.onchange('product_id', 'reason_id')
    def _onchange_product_id(self):
        self.name = self.product_id.name
        if not self.reason_id:
            self.reason_id = self.picking_id.location_id.id \
                if self.picking_id.other_import else self.picking_id.location_dest_id.id
        if not self.reason_type_id:
            self.reason_type_id = self.picking_id.reason_type_id.id
        if not self.reason_id.is_price_unit:
            self.amount_total = self.product_id.standard_price * self.product_uom_qty

    def _account_entry_move(self, qty, description, svl_id, cost):
        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        for item in res:
            if 'date' in item and self.picking_id.date_done:
                item['date'] = fields.Datetime.context_timestamp(self, self.picking_id.date_done).date()
        if self.picking_id.picking_type_id.code != 'incoming':
            return res
        return res

    def _get_price_unit(self):
        if self.amount_total != 0 and self.product_uom_qty != 0:
            self.price_unit = round(self.amount_total/self.product_uom_qty)
        res = super()._get_price_unit()
        order = self.purchase_line_id.order_id
        if (order.currency_id != self.env.company.currency_id and order.exchange_rate > 0) and not (self.origin_returned_move_id or self.purchase_line_id.order_id.is_return):
            res = res * order.currency_id.rate * order.exchange_rate
        return res

    def write(self, vals):
        for item in self:
            if item.picking_id.date_done:
                vals['date'] = item.picking_id.date_done
                account_move_ids = self.env['account.move'].search([('stock_move_id', 'in', item.ids)])
                if account_move_ids:
                    account_move_ids.write({
                        'date': fields.Datetime.context_timestamp(self, item.picking_id.date_done).date()
                    })
        return super().write(vals)
    
    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        rslt = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        rslt['credit_line_vals'].update({
            'occasion_code_id': self.occasion_code_id.id or False,
            'production_order': self.work_production.id or False,
            'work_order': self.work_production.id or False,
            'analytic_account_id': self.account_analytic_id.id or False,
            'account_analytic_id': self.account_analytic_id.id or False,
        })
        rslt['debit_line_vals'].update({
            'occasion_code_id': self.occasion_code_id.id or False,
            'production_order': self.work_production.id or False,
            'work_order': self.work_production.id or False,
            'analytic_account_id': self.account_analytic_id.id or False,
            'account_analytic_id': self.account_analytic_id.id or False,
        })
        return rslt
