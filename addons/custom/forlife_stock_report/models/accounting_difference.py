from odoo import fields, api, models, _
import datetime
from datetime import timedelta


class CalculateFinalValueInherit(models.Model):
    _name = 'accounting.difference'
    _description = 'Xử lệnh chênh lệch'

    name = fields.Char(compute='compute_from_to_date', string='Tên', store=True)
    month = fields.Char(string='Tháng', default=fields.Date.today().month, required=True)
    year = fields.Char(string='Năm', default=fields.Date.today().year, required=True)
    from_date = fields.Date(string='Từ ngày', compute='compute_from_to_date', store=True)
    to_date = fields.Date(string='Đến ngày', compute='compute_from_to_date', store=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    account_ids = fields.Many2many('account.account', 'account_diff_account_id', 'ad_id', 'ac_id', string='Tải khoản')
    purchase_ids = fields.Many2many('purchase.order', 'ad_po_rel', 'ad_id', 'po_id', string='Đơn hàng')
    diff_lines = fields.One2many('accounting.difference.line', 'parent_id', string='Chi tiết chênh lệch')
    move_ids = fields.Many2many('account.move', 'calculate_final_move_rel', 'cf_id', 'move_id',
                                string='Bút toán chênh lệch')
    move_count = fields.Integer(string='Số bút toán', compute='compute_move_count')
    state = fields.Selection([('draft', 'Dự thảo'), ('posted', 'Đã vào sổ')], string='Trạng thái', default='draft')

    def first_and_last_day_of_month(self, year, month):
        # Tạo một ngày đầu tiên của tháng
        first_day = datetime.date(year, month, 1)
        # Xác định tháng tiếp theo
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        # Tạo ngày cuối cùng của tháng bằng cách lấy ngày cuối cùng của tháng trước và trừ đi một ngày
        last_day = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)
        return first_day, last_day

    @api.depends('month', 'year')
    def compute_from_to_date(self):
        for rec in self:
            current_date = datetime.date.today()
            current_year = current_date.replace(year=int(rec.year)).year
            current_month = current_date.replace(year=int(rec.year), month=int(rec.month)).month
            first, last = self.first_and_last_day_of_month(current_year, current_month)
            rec.from_date = first
            rec.to_date = last
            rec.name = 'Xử lý chênh lệch tháng %s năm %s' % (rec.month, rec.year)


    @api.depends('move_ids')
    def compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.move_ids)

    def action_view_invoice(self):
        self.ensure_one()
        move_ids = self.move_ids.ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False},
            "name": _("Bút toán chênh lệch"),
            'view_mode': 'tree,form',
        }
        return result

    def is_account_stock(self, categ_id):
        self._cr.execute("""
                select split_part(value_reference, ',', 2) account from ir_property ip 
                where name = 'property_stock_account_input_categ_id' 
                and company_id = %s and res_id = 'product.category,' || %s limit 1;
            """, params=(self.env.company.id, categ_id))
        data = self._cr.dictfetchone()
        return data.get('account')

    def _sql_string(self):
        return """
                with invoice_purchase as (
                select
                    pp.id product_id,
                    aa.id account_stock_id,
                    aml.account_id account_source_id,
                    max(aa.code) account_code,
                    sum(aml.debit) debit,
                    0 credit,
                    po.id purchase_id,
                    pol.id purchase_line_id,
                    0 stock_move_id
                from
                    account_move_line aml
                join account_move am on
                    aml.move_id = am.id
                join product_product pp on
                    pp.id = aml.product_id
                join product_template pt on
                    pp.product_tmpl_id = pt.id
                join account_account aa on aml.account_id = aa.id
                join product_category pc on
                    pt.categ_id = pc.id
                join ir_property ip on
                    ip.res_id = 'product.category,' || pt.categ_id
                    and ip."name" = 'property_stock_valuation_account_id'
                    and ip.company_id = 3
                    and ip.value_reference = 'account.account,' || aa.id
                join purchase_order_line pol on
                    aml.purchase_line_id = pol.id
                join purchase_order po on
                    pol.order_id = po.id
                where
                    po.company_id = {company_id}
                    and am.state = 'posted' and am.date between '{from_date}' and '{to_date} 23:59:59'
                group by
                    pp.id,
                    aa.id,
                    po.id,
                    aml.account_id,
                    pol.id
                union all
                select
                    pp.id product_id,
                    aa.id account_stock_id,
                    aml.account_id account_source_id,
                    max(aa.code) account_code,
                    0 debit,
                    sum(aml.credit) credit,
                    po.id purchase_id,
                    pol.id purchase_line_id,
                    sm.id stock_move_id
                from
                    account_move_line aml
                join account_move am on
                    aml.move_id = am.id
                join product_product pp on
                    pp.id = aml.product_id
                join product_template pt on
                    pp.product_tmpl_id = pt.id
                join account_account aa on aml.account_id = aa.id
                join product_category pc on
                    pt.categ_id = pc.id
                join ir_property ip on
                    ip.res_id = 'product.category,' || pt.categ_id
                    and ip."name" = 'property_stock_valuation_account_id'
                    and ip.company_id = 3
                    and ip.value_reference = 'account.account,' || aa.id
                join stock_move sm on
                    am.stock_move_id = sm.id
                join purchase_order_line pol on
                    pol.id = sm.purchase_line_id
                join purchase_order po on
                    pol.order_id = po.id
                where
                    po.company_id = {company_id}
                    and am.state = 'posted' and am.date between '{from_date}' and '{to_date} 23:59:59'
                group by
                    pp.id,
                    aa.id,
                    po.id,
                    am.id,
                    aml.account_id,
                    pol.id,
                    sm.id
                )

                select
                    {parent_id} parent_id,
                    ip.product_id,
                    ip.account_stock_id,
                    ip.account_source_id,
                    sum(debit) debit,
                    sum(credit) credit,
                    (sum(debit) - sum(credit)) diff,
                    ip.purchase_id,
                    ip.purchase_line_id,
                    max(ip.stock_move_id) stock_move_id
                from
                    invoice_purchase ip
                {where}
                group by
                    ip.product_id,
                    ip.account_stock_id,
                    ip.account_source_id,
                    ip.purchase_id,
                    parent_id,
                    ip.purchase_line_id
                having sum(debit) <> 0 and sum(credit) <> 0
            """

    def get_data_diff(self):
        self.diff_lines.unlink()
        where_string = 'where 1 = 1'
        if self.account_ids:
            where_string += f' and ip.account_source_id = any(array{self.account_ids.ids})'
        if self.purchase_ids:
            where_string += f' and ip.purchase_id = any(array{self.purchase_ids.ids})'
        query = self._sql_string().format(
            company_id=self.env.company.id,
            from_date=self.from_date,
            to_date=self.to_date,
            parent_id=self.id,
            where=where_string,
        )
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        self.env['accounting.difference.line'].create(data)

    def prepare_value_by_diff(self):
        journal = self.env['account.journal']
        journal_up_id = journal.search([
            ('code', '=', 'GL01'),
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        journal_down_id = journal.search([
            ('code', '=', 'GL02'),
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        purchase_ids = self.diff_lines.mapped('purchase_id')
        vals = []
        for purchase in purchase_ids:
            for line in self.diff_lines.filtered(lambda x: x.purchase_id == purchase):
                if line.diff == 0:
                    continue
                vals.append({
                    'date': self.to_date,
                    'ref': self.name,
                    'journal_id': journal_up_id.id if line.diff > 0 else journal_down_id.id,
                    'stock_move_id': line.stock_move_id.id if self.is_account_stock(line.product_id.categ_id.id) == str(
                        line.account_source_id.id) else False,
                    'auto_post': 'no',
                    'x_root': 'other',
                    'end_period_entry': True,
                    'line_ids': [
                        (0, 0, {
                            'name': self.name,
                            'product_id': line.product_id.id,
                            'purchase_line_id': line.purchase_line_id.id,
                            'quantity': 0,
                            'credit': line.diff if line.diff > 0 else -line.diff,
                            'account_id': line.account_source_id.id if line.diff > 0 else line.account_stock_id.id
                        }),
                        (0, 0, {
                            'name': self.name,
                            'product_id': line.product_id.id,
                            'purchase_line_id': line.purchase_line_id.id,
                            'quantity': 0,
                            'debit': line.diff if line.diff > 0 else -line.diff,
                            'account_id': line.account_stock_id.id if line.diff > 0 else line.account_source_id.id
                        }),
                    ],
                    'move_type': 'entry',
                    'stock_valuation_layer_ids': [(0, 0, {
                        'value': line.diff if line.diff > 0 else -line.diff,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'description': self.name,
                        'product_id': line.product_id.id,
                        'company_id': self.env.company.id
                    })]
                })

        return vals

    def action_create_account_move (self):
        move_vals = self.prepare_value_by_diff()
        account_move = self.env['account.move'].create(move_vals)
        self.move_ids = [(6, 0, account_move.ids)]


class AccountingDifferenceLine(models.Model):
    _name = 'accounting.difference.line'
    _description = 'Hạch toán chênh lệnh'

    parent_id = fields.Many2one('accounting.difference', string='Phiếu hạch toán', ondelete='cascade')
    account_source_id = fields.Many2one('account.account', string='Tài khoản nguồn')
    purchase_id = fields.Many2one('purchase.order', string='Đơn mua')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Chi tiết đơn mua')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    account_stock_id = fields.Many2one('account.account', string='Tài khoản kho')
    debit = fields.Float(string='Phát sinh nợ')
    credit = fields.Float(string='Phát sinh có')
    diff = fields.Float(string='Chênh lệch')
    diff_rate = fields.Float(string='Tỉ lệ chênh lệch', compute='_compute_diff_rate')
    stock_move_id = fields.Many2one('stock.move', string='Chi tiết điều chuyển')

    def _compute_diff_rate(self):
        for rec in self:
            rec.diff_rate = (rec.diff / (rec.debit + rec.credit)) * 100

