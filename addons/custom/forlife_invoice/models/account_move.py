from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    account_expense_labor_detail_ids = fields.One2many('account.expense.labor.detail', 'move_id', string='Account Expense Labor Detail')
    sum_expense_labor_ids = fields.One2many('summary.expense.labor.account', 'move_id', string='Summary Expense Labor')
    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')
    origin_invoice_id = fields.Many2one('account.move', string='Origin Invoice', readonly=True, check_company=True)
    increase_decrease_inv_count = fields.Integer(compute="_compute_increase_decrease_inv_count", string='Increase/decrease invoice count')

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'total_trade_discount',
        'x_amount_tax',
        'state')
    def _compute_amount(self):
        super()._compute_amount()
        for record in self.filtered(lambda x: x.total_trade_discount or x.x_amount_tax):
            amount_residual = record.amount_residual - (record.total_trade_discount + record.x_amount_tax)
            record.amount_residual = amount_residual

    def _compute_increase_decrease_inv_count(self):
        for move in self:
            move.increase_decrease_inv_count = self.search_count([('origin_invoice_id', '=', move.id)])

    def action_view_increase_decrease_invoice(self):
        self.ensure_one()
        invoices = self.search([('origin_invoice_id', 'in', self.ids)])
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        if len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = invoices.id
        else:
            result['domain'] = [('id', 'in', invoices.ids)]
        return result

    def button_popup_increase_decrease_invoice(self):
        return {
            'name': 'Tăng/giảm hóa đơn',
            'domain': [],
            'res_model': 'wizard.increase.decrease.invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'default_origin_invoice_id': self.id},
            'target': 'new',
        }

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        if not res.purchase_order_product_id or res.purchase_order_product_id[0].is_inter_company != False:
            return res
        for line in res.invoice_line_ids:
            if line.product_id:
                line._compute_account_id()
        return res
    
    def action_post(self):
        for rec in self:
            rec.create_invoice_expense_purchase()
        return super(AccountMove, self).action_post()
    
    @api.onchange('account_expense_labor_detail_ids',
                  'account_expense_labor_detail_ids.totals_back',
                  'account_expense_labor_detail_ids.price_subtotal_back')
    def _onchange_account_expense_labor_detail(self):
        for item in self:
            if item.account_expense_labor_detail_ids:
                item.create_invoice_expense_purchase()
    
    def create_invoice_expense_purchase(self):
        if not self.origin_invoice_id or self.move_type not in ('in_invoice','in_refund'):
            return
        if self.select_type_inv not in ('labor','expense'):
            return
        if not self.account_expense_labor_detail_ids:
            return
        return self._create_invoice_expense_purchase()
        
    # Hóa đơn chi phí mua hàng nhiều PO
    def _create_invoice_expense_purchase(self):
        invoice_line_ids = [(5,0,0)]
        purchase_id = self.purchase_order_product_id[0]
        if not purchase_id:
            return
        if not purchase_id.cost_line:
            return
        picking_ids = self.receiving_warehouse_id.filtered(lambda x: x.state == 'done')
        picking_in_ids = picking_ids.filtered(lambda x: not x.x_is_check_return)
        if not picking_in_ids:
            return

        pending_section = None
        total_vnd_amount_order = sum(purchase_id.order_line.mapped('total_vnd_amount'))
        if total_vnd_amount_order <= 0:
            raise UserError(_('Tổng tiền chi phí không được nhỏ hơn hoặc bằng 0. Vui lòng kiểm tra lại!'))

        for cost_line in self.account_expense_labor_detail_ids:
            for line in purchase_id.order_line:

                move_ids = line.move_ids.filtered(lambda x: x.picking_id in picking_ids and x.state == 'done')
                move_return_ids = move_ids.mapped('returned_move_ids').filtered(lambda x: x.state == 'done')

                # lấy tổng SL hoàn thành trừ tổng SL trả của 1 dòng purchase order line
                move_qty = sum(move_ids.mapped('quantity_done')) - sum(move_return_ids.mapped('quantity_done'))

                if not total_vnd_amount_order or not line.product_qty or move_qty <= 0:
                    return

                amount_rate = line.total_vnd_amount / total_vnd_amount_order
                cp = ((amount_rate * cost_line.totals_back) / line.product_qty) * move_qty
                # currency_id = self.currency_id.id
                # if cost_line.currency_id.id != currency_id:
                #     rate = cost_line.exchange_rate/self.exchange_rate
                #     cp = cp * rate

                data_line = self._prepare_invoice_expense_line(cost_line, line, cp)
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if pending_section:
                    line_vals = pending_section._prepare_account_move_line()
                    line_vals.update(data_line)
                    invoice_line_ids.append((0, 0, line_vals))
                    pending_section = None
                line_vals = line._prepare_account_move_line()
                line_vals.update(data_line)
                invoice_line_ids.append((0, 0, line_vals))
        self.invoice_line_ids = invoice_line_ids


    def _prepare_invoice_expense_line(self, cost_line, po_line, cp):
        data_line = {
            'product_id': po_line.product_id.id,
            'product_expense_origin_id': cost_line.product_id.id,
            'description': po_line.product_id.name,
            'account_id': cost_line.product_id.categ_id.property_stock_account_input_categ_id.id,
            'name': cost_line.product_id.name,
            'quantity': 1,
            'price_unit': cp,
            'occasion_code_id': po_line.occasion_code_id.id if po_line.occasion_code_id else False,
            'work_order': po_line.production_id.id if po_line.production_id else False,
            'account_analytic_id': po_line.account_analytic_id.id if po_line.account_analytic_id else False,
            'import_tax': po_line.import_tax,
            'tax_ids': [(6, 0, cost_line.tax_percent.ids)]
        }
        return data_line

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
    expense_est_labor = fields.Float(string='CP ước tính nhân công', currency_field='currency_id')

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

            lines = rec.move_id.invoice_line_ids.filtered(lambda x: x.product_id == rec.product_id and x.product_expense_origin_id and x.product_expense_origin_id.x_type_cost_product == 'labor_costs')
            rec.expense_est_labor = sum(lines.mapped('price_unit'))

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
