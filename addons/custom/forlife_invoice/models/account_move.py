from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    account_expense_labor_detail_ids = fields.One2many('account.expense.labor.detail', 'move_id', string='Account Expense Labor Detail')
    sum_expense_labor_ids = fields.One2many('summary.expense.labor.account', 'move_id', string='Summary Expense Labor')

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        if not res.purchase_order_product_id or res.purchase_order_product_id[0].is_inter_company != False:
            return res
        for line in res.invoice_line_ids:
            if line.product_id:
                line._compute_account_id()
        return res

class AccountTax(models.Model):
    _inherit = 'account.tax.repartition.line'

    product_id = fields.Many2one('product.product', string='Sản phẩm')

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        if self.picking_id:
            for item in new_picking:
                item.write({
                    'x_is_check_return': True,
                    'origin': self.picking_id.origin,
                    'relation_return': self.picking_id.name
                })
            for item in self.picking_id.move_line_ids_without_package:
                for line in new_picking.move_line_ids_without_package:
                    if item.product_id == line.product_id:
                        line.write({
                            'po_id': item.po_id
                        })
        return new_picking_id, pick_type_id


class AccountExpenseLaborDetail(models.Model):
    _name = 'account.expense.labor.detail'

    move_id = fields.Many2one('account.move', string='Account Move')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    description = fields.Char('Mô tả')
    uom_id = fields.Many2one('uom.uom', string='Đơn vị')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', store=True, related='move_id.currency_id')
    company_id = fields.Many2one(related='move_id.company_id', string='Công ty', store=True)
    qty = fields.Float('Số lượng')
    price_subtotal_back = fields.Float(string='Thành tiền', currency_field='currency_id')
    tax_back = fields.Float(string='Tiền thuế', currency_field='currency_id')
    totals_back = fields.Float(string='Tổng tiền sau thuế', compute='compute_totals_back', currency_field='currency_id')
    tax_percent = fields.Many2one('account.tax', string='% Thuế')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountExpenseLaborDetail, self).create(vals_list)
        return res

    @api.depends('tax_back', 'price_subtotal_back')
    def compute_totals_back(self):
        for rec in self:
            rec.totals_back = rec.price_subtotal_back + rec.tax_back


class SummaryExpenseLaborAccount(models.Model):
    _name = 'summary.expense.labor.account'

    move_id = fields.Many2one('account.move', string='Account Move')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    description = fields.Char('Mô tả')
    uom_id = fields.Many2one('uom.uom', string='Đơn vị tính')
    price_unit = fields.Float(' Đơn giá')
    product_po_qty = fields.Float('Po Quantity', compute='_compute_quantity_po')
    product_qty = fields.Float('Quantity', compute='_compute_quantity')
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, related='move_id.currency_id')
    origin_currency_id = fields.Many2one('res.currency', string='Origin Currency')
    company_id = fields.Many2one(related='move_id.company_id', string='Company', store=True)
    before_tax = fields.Float(string='CP thực tế trước thuế', compute='_compute_before_tax', currency_field='currency_id')
    after_tax = fields.Float(string='CP thực tế sau thuế', compute='_compute_after_tax', currency_field='currency_id')
    expense_labor = fields.Float(string='CP thưc tế nhân công', compute='_compute_expense_labor')
    qty_actual = fields.Float(string='SL(thực nhập)', compute='_compute_qty_actual')
    before_est_tax = fields.Float(string='CP ước tính trước thuế', currency_field='currency_id')
    after_est_tax = fields.Float(string='CP ước tính sau thuế', currency_field='currency_id')
    expense_est_labor = fields.Float(string='CP ước tính nhân công', currency_field='currency_id', compute='_compute_expense_est_labor')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SummaryExpenseLaborAccount, self).create(vals_list)
        for rec in res:
            cost_line_true = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
            before_est_tax = sum(rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_true.mapped('product_id')).mapped('price_unit'))
            rec.before_est_tax = before_est_tax

            cost_line_false = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
            after_est_tax = sum(rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_false.mapped('product_id')).mapped('price_unit'))
            rec.after_est_tax = after_est_tax
        return res

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id.id

    @api.depends('move_id.receiving_warehouse_id', 'product_id')
    def _compute_qty_actual(self):
        for item in self:
            if item.move_id.receiving_warehouse_id:
                move_ids = item.move_id.receiving_warehouse_id.mapped('move_ids')
                qty = sum(move_ids.filtered(lambda x: x.product_id == item.product_id).mapped('quantity_done'))
                qty_return = sum(move_ids.filtered(lambda x: x.product_id == item.product_id)
                                 .mapped('returned_move_ids').filtered(lambda x: x.state == 'done').mapped('quantity_done'))
                item.qty_actual = qty - qty_return
            else:
                item.qty_actual = 0

    @api.depends('product_id', 'move_id.purchase_order_product_id')
    def _compute_quantity_po(self):
        for item in self:
            item.product_po_qty = 0
            if item.product_id and item.move_id.purchase_order_product_id:
                pol_ids = item.move_id.purchase_order_product_id.mapped('order_line').filtered(lambda x: x.product_id == item.product_id)
                item.product_po_qty = sum(x.product_qty for x in pol_ids)

    @api.depends('move_id.receiving_warehouse_id', 'product_id')
    def _compute_quantity(self):
        for item in self:
            item.product_qty = 0
            if item.product_id and item.move_id.receiving_warehouse_id:
                move_ids = item.move_id.receiving_warehouse_id.mapped('move_ids').filtered(lambda w: w.product_id == item.product_id)
                item.product_qty = sum(x.quantity_done for x in move_ids)

    # @api.depends('product_id', 'move_id.cost_line')
    # def compute_origin_est_tax(self):
    #     for rec in self:
    #         cost_line_true = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
    #         before_est_tax = sum(rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_true.mapped('product_id')).mapped('price_unit'))
    #         rec.before_est_tax = before_est_tax
    #
    #         cost_line_false = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
    #         after_est_tax = sum(rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_false.mapped('product_id')).mapped('price_unit'))
    #         rec.after_est_tax = after_est_tax

    @api.depends('product_id', 'move_id.cost_line.is_check_pre_tax_costs', 'move_id.invoice_line_ids')
    def _compute_before_tax(self):
        for rec in self:
            cost_line_true = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
            total_cost_true = sum(cost_line_true.cost_line_origin.mapped('cost_paid'))
            if rec.move_id.vendor_back_ids:
                lines = rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_true.mapped('product_id'))
                total_cost_true += sum([x.price_unit for x in lines])
            rec.before_tax = total_cost_true

    @api.depends('product_id', 'move_id.cost_line.is_check_pre_tax_costs', 'move_id.invoice_line_ids')
    def _compute_after_tax(self):
        for rec in self:
            cost_line_false = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
            total_cost_false = sum(cost_line_false.cost_line_origin.mapped('cost_paid'))
            if rec.move_id.vendor_back_ids:
                lines = rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_false.mapped('product_id'))
                total_cost_false += sum([x.price_unit for x in lines])
            rec.after_tax = total_cost_false

    @api.depends('product_id', 'move_id.invoice_line_ids', 'move_id.invoice_line_ids.product_expense_origin_id')
    def _compute_expense_labor(self):
        for item in self:
            total = 0
            lines = item.move_id.invoice_line_ids.filtered(lambda x: x.product_id == item.product_id and x.product_expense_origin_id and x.product_expense_origin_id.x_type_cost_product == 'labor_costs')
            total += sum([x.price_unit for x in lines])
            item.expense_labor = total

    @api.depends('product_id', 'move_id.invoice_line_ids', 'move_id.invoice_line_ids.product_expense_origin_id')
    def _compute_expense_est_labor(self):
        for item in self:
            lines = item.move_id.invoice_line_ids.filtered(lambda x: x.product_id == item.product_id and x.product_expense_origin_id and x.product_expense_origin_id.x_type_cost_product == 'labor_costs')
            item.expense_labor = sum(lines.mapped('price_unit'))

