from odoo import fields, api, models, _
import datetime
from odoo.exceptions import ValidationError


class CalculateFinalValue(models.Model):
    _name = 'calculate.final.value'
    _description = 'Tính giá trị cuối kỳ'

    name = fields.Char(compute='compute_from_to_date', string='Kỳ tính giá', store=True)
    month = fields.Char(string='Tháng', default=fields.Date.today().month, required=True)
    year = fields.Char(string='Năm', default=fields.Date.today().year, required=True)
    from_date = fields.Date(string='Từ ngày', compute='compute_from_to_date', store=True)
    to_date = fields.Date(string='Đến ngày', compute='compute_from_to_date', store=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    category_type_id = fields.Selection([
        ('npl_ccdc', 'Nguyên phụ liệu/CCDC'),
        ('tp_hh', 'Thành phẩm/Hàng hóa'),
    ], string='Loại sản phẩm', required=True)
    state = fields.Selection([
        ('step1', 'Đơn giá bình quân'),
        ('step2', 'Bảng kê chênh lệch'),
        ('step3', 'Hạch toán lần 1'),
        ('step4', 'Hạch toán lần 2'),
    ], default='step1', string='Trạng thái')
    entry1_ids = fields.Many2many(
        'account.move',
        'calculate_final_entry1_move_rel', 'cf_id', 'move_id',
        string='Bút toán chênh lệch')
    entry1_count = fields.Float(string='Số lượng hóa đơn', compute='entry_count')

    entry2_ids = fields.Many2many(
        'account.move',
        'calculate_final_entry2_move_rel', 'cf_id', 'move_id',
        string='Bút toán chênh lệch')
    entry2_count = fields.Float(string='Số lượng hóa đơn', compute='entry_count')

    @api.depends('entry1_ids', 'entry2_ids')
    def entry_count(self):
        for rec in self:
            rec.entry1_count = len(rec.entry1_ids)
            rec.entry2_count = len(rec.entry2_ids)

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
            rec.name = 'Kỳ tính giá tháng %s năm %s' % (rec.month, rec.year)

    @api.constrains('category_type_id')
    def _constrains_category_type_id(self):
        for rec in self:
            record_valid = rec.search([('from_date', '=', rec.from_date), ('to_date', '=', rec.to_date), ('id', '!=', rec.id)])
            if rec.category_type_id == 'tp_hh' and len(record_valid.filtered(lambda x: x.category_type_id == 'tp_hh')) >= 1:
                raise ValidationError('Đã tồn tại kỳ tính phí với loại sản phẩm Thành phẩm/Hàng hóa cùng kỳ không thể tạo mới.')
            if rec.category_type_id == 'npl_ccdc' and len(record_valid.filtered(lambda x: x.category_type_id == 'npl_ccdc')) >= 1:
                raise ValidationError('Đã tồn tại kỳ tính phí với loại sản phẩm Nguyên phụ liệu/CCCD cùng kỳ không thể tạo mới.')
            if rec.category_type_id == 'tp_hh' and not record_valid.filtered(lambda x: x.category_type_id == 'npl_ccdc'):
                raise ValidationError('Bạn không thể tính giá cuối kỳ cho loại sản phẩm Thành phẩm/Hàng hóa \ntrước khi tính giá cuối kỳ cho loại sản phẩm Nguyên liệu/CCCD.')

    @api.onchange('category_type_id')
    def _onchange_category_type_id(self):
        for rec in self:
            record_valid = rec.search([('category_type_id', '=', 'npl_ccdc'), ('from_date', '=', rec.from_date), ('to_date', '=', rec.to_date)])
            if rec.category_type_id == 'tp_hh' and not record_valid:
                raise ValidationError('Bạn không thể tính giá cuối kỳ cho loại sản phẩm Thành phẩm/Hàng hóa \ntrước khi tính giá cuối kỳ cho loại sản phẩm Nguyên liệu/CCCD')

    def prepare_value_by_diff(self, data):
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

        vals = []
        for key, val in data.items():
            if val['sum'] == 0:
                continue
            product = self.env['product.product'].browse(key)
            lines = [
                (0, 0, {
                    'name': self.name,
                    'product_id': product.id,
                    'quantity': 0,
                    'credit': amount if val['sum'] > 0 else -amount,
                    'account_id': account
                }) for account, amount in val['account'].items()
            ]
            lines.append((0, 0, {
                'name': self.name,
                'product_id': product.id,
                'quantity': 0,
                'debit': val['sum'] if val['sum'] > 0 else -val['sum'],
                'account_id': product.categ_id.property_stock_valuation_account_id.id
            }))

            vals.append({
                'date': self.to_date,
                'ref': self.name,
                'journal_id': journal_up_id.id if val['sum'] > 0 else journal_down_id.id,
                'auto_post': 'no',
                'x_root': 'other',
                'end_period_entry': True,
                'line_ids': lines,
                'move_type': 'entry',
                'stock_valuation_layer_ids': [(0, 0, {
                    'value': amount if val['sum'] > 0 else -amount,
                    'unit_cost': 0,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'description': self.name,
                    'product_id': product.id,
                    'company_id': self.env.company.id
                }) for account, amount in val['account'].items()]
            })

        return vals

    def create_invoice_diff_entry1(self):
        if self.state != 'step2':
            raise ValidationError('Bản chỉ có thể thực hiện khi đã hoàn thành bảng kê chênh lệch')
        self.entry1_ids.unlink()
        sql_product = """
            select 
                product_id,
                account_id,
                sum(amount_diff) amount_diff
            from list_exported_goods_diff
            where parent_id = {parent_id}
            group by product_id, account_id 
        """.format(parent_id=self.id)
        self._cr.execute(sql_product)
        data_product = self._cr.dictfetchall()
        products = {}
        for product in data_product:
            if product['product_id'] in products:
                products[product['product_id']]['account'].update({product['account_id']: product['amount_diff']})
                products[product['product_id']]['sum'] += product['amount_diff']
            else:
                products.update({product['product_id']: {
                    'account': {product['account_id']: product['amount_diff']},
                    'sum': product['amount_diff']
                }})
        move_vals = self.prepare_value_by_diff(data=products)
        moves = self.env['account.move'].create(move_vals)
        # cập nhật lại giá vốn
        for svl in moves.stock_valuation_layer_ids:
            self.env['stock.move'].update_standard_price_product(svl.product_id)
        self.write({
            'entry1_ids': [(6, 0, moves.ids)],
            'state': 'step3'
        })

    def create_invoice_diff_entry2(self):
        if self.state != 'step2':
            raise ValidationError('Bản chỉ có thể thực hiện khi đã hoàn thành bảng kê chênh lệch')
        self.entry2_ids.unlink()
        sql_product = """
            select 
                product_end_id,
                account_id,
                sum(amount_diff) amount_diff
            from list_exported_goods_diff
            where parent_id = {parent_id} and product_end_id <> 0
            group by product_end_id, account_id 
        """.format(parent_id=self.id)
        self._cr.execute(sql_product)
        data_product = self._cr.dictfetchall()
        products = {}
        for product in data_product:
            if product['product_id'] in products:
                products[product['product_id']]['account'].update({product['account_id']: product['amount_diff']})
                products[product['product_id']]['sum'] += product['amount_diff']
            else:
                products.update({product['product_id']: {
                    'account': {product['account_id']: product['amount_diff']},
                    'sum': product['amount_diff']
                }})
        move_vals = self.prepare_value_by_diff(data=products)
        moves = self.env['account.move'].create(move_vals)

        # cập nhật lại giá vốn
        for svl in moves.stock_valuation_layer_ids:
            self.env['stock.move'].update_standard_price_product(svl.product_id)
        self.write({
            'entry2_ids': [(6, 0, moves.ids)],
            'state': 'step4'
        })

    def action_view_entry1(self):
        self.ensure_one()
        move_ids = self.entry1_ids.ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False},
            "name": _("Bút toán chênh lệch sản phẩm nguồn"),
            'view_mode': 'tree,form',
        }
        return result

    def action_view_entry2(self):
        self.ensure_one()
        move_ids = self.entry2_ids.ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False},
            "name": _("Bút toán chênh lệch sản phẩm đích"),
            'view_mode': 'tree,form',
        }
        return result
