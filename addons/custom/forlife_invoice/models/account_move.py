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
    company_id = fields.Many2one(related='move_id.company_id', stirng='Công ty', store=True)
    qty = fields.Float('Số lượng')
    price_subtotal_back = fields.Float(string='Thành tiền')
    tax_back = fields.Float(string='Tiền thuế', compute='compute_tax')
    totals_back = fields.Float(string='Tổng tiền sau thuế', compute='compute_totals_back')
    tax_percent = fields.Many2one('account.tax', string='% Thuế')

    @api.depends('tax_percent', 'price_subtotal_back')
    def compute_tax(self):
        for rec in self:
            rec.tax_back = rec.price_subtotal_back * rec.tax_percent.amount * 0.01

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
    # total_vnd_amount = fields.Monetary('Total VND Amount', compute='_compute_total_vnd_amount')
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, related='move_id.currency_id')
    company_id = fields.Many2one(related='move_id.company_id', stirng='Company', store=True)

    before_tax = fields.Float(string='Chi phí trước tính thuế', compute='_compute_before_tax')
    after_tax = fields.Float(string='Chi phí sau thuế (TNK - TTTDT)', compute='_compute_after_tax')
    # expense_labor = fields.Float(string='Chi phí nhân công', compute='_compute_expense_labor')
    # total_product = fields.Float(string='Tổng giá trị tiền hàng',
    #                              compute='_compute_total_product')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id.id

    # @api.depends('price_unit', 'product_qty', 'move_id.exchange_rate')
    # def _compute_total_vnd_amount(self):
    #     for rec in self:
    #         rec.total_vnd_amount = rec.price_unit * rec.product_qty * rec.move_id.exchange_rate

    @api.depends('product_id', 'move_id.purchase_order_product_id')
    def _compute_quantity_po(self):
        for item in self:
            item.product_po_qty = 0
            if item.product_id and item.move_id.purchase_order_product_id:
                pol_ids = item.move_id.purchase_order_product_id.mapped('order_line')\
                    .filtered(lambda x: x.product_id == item.product_id)
                item.product_po_qty = sum(x.product_qty for x in pol_ids)

    @api.depends('move_id.receiving_warehouse_id', 'product_id')
    def _compute_quantity(self):
        for item in self:
            item.product_qty = 0
            if item.product_id and item.move_id.receiving_warehouse_id:
                move_ids = item.move_id.receiving_warehouse_id.mapped('move_ids').filtered(lambda w: w.product_id == item.product_id)
                item.product_qty = sum(x.quantity_done for x in move_ids)

    @api.depends('product_id', 'move_id.cost_line.is_check_pre_tax_costs', 'move_id.invoice_line_ids')
    def _compute_before_tax(self):
        for rec in self:
            rec.before_tax = 0
            total_cost_true = 0
            cost_line_true = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == True)
            lines = rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_true.mapped('product_id'))
            total_cost_true += sum([x.price_unit for x in lines])
            rec.before_tax = total_cost_true

    @api.depends('product_id', 'move_id.cost_line.is_check_pre_tax_costs',
                 'move_id.invoice_line_ids')
    def _compute_after_tax(self):
        for rec in self:
            rec.after_tax = 0
            total_cost_false = 0
            cost_line_false = rec.move_id.cost_line.filtered(lambda r: r.is_check_pre_tax_costs == False)
            lines = rec.move_id.invoice_line_ids.filtered(
                lambda x: x.product_id == rec.product_id and x.product_expense_origin_id in cost_line_false.mapped(
                    'product_id'))
            total_cost_false += sum([x.price_unit for x in lines])
            rec.after_tax = total_cost_false

    # @api.depends('product_id', 'move_id.invoice_line_ids', 'move_id.invoice_line_ids.product_expense_origin_id')
    # def _compute_expense_labor(self):
    #     for item in self:
    #         item.expense_labor = 0
    #         total = 0
    #         lines = item.move_id.invoice_line_ids.filtered(
    #             lambda x: x.product_id == item.product_id and x.product_expense_origin_id in cost_line_false.mapped(
    #                 'product_id'))

