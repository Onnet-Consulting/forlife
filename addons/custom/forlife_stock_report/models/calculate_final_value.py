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
    product_type = fields.Selection([('source', 'Sản phẩm nguồn'), ('end', 'Sản phẩm đích')], string='Loại sản phẩm', required=True)
    state = fields.Selection([
        ('step1', 'Đơn giá bình quân'),
        ('step2', 'Bảng kê chênh lệch'),
        ('step3', 'Hạch toán'),
        ('step4', 'Done'),
    ], default='step1', string='Trạng thái')
    entry_ids = fields.Many2many(
        'account.move',
        'calculate_final_entry_move_rel', 'cf_id', 'move_id',
        string='Bút toán chênh lệch')
    entry_count = fields.Float(string='Số lượng hóa đơn', compute='compute_entry_count')

    @api.depends('entry_ids')
    def compute_entry_count(self):
        for rec in self:
            rec.entry_count = len(rec.entry_ids)

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
            record_valid = rec.search([('category_type_id', '=', 'npl_ccdc'), ('from_date', '=', rec.from_date),
                                       ('to_date', '=', rec.to_date), ('state', '=', 'step4')])
            if rec.category_type_id == 'npl_ccdc' and rec.product_type == 'end' and not record_valid:
                raise ValidationError(
                    'Bạn không thể tính giá cuối kỳ cho loại sản phẩm Nguyên liệu/CCCD đích \ntrước khi hoàn thành tính giá cuối kỳ cho loại sản phẩm Nguyên liệu/CCCD nguồn')
            if rec.category_type_id == 'tp_hh' and (not record_valid or (record_valid[-1].product_type == 'end' and record_valid[-1].state != 'step4')):
                raise ValidationError(
                    'Bạn không thể tính giá cuối kỳ cho loại sản phẩm Thành phẩm/Hàng hóa \ntrước khi hoàn thành tính giá cuối kỳ cho loại sản phẩm Nguyên liệu/CCCD')

            record_valid_hh = rec.search([('category_type_id', '=', 'tp_hh'), ('from_date', '=', rec.from_date),
                                          ('to_date', '=', rec.to_date), ('state', '=', 'step4')])
            if rec.category_type_id == 'tp_hh' and rec.product_type == 'end' and not record_valid_hh:
                raise ValidationError(
                    'Bạn không thể tính giá cuối kỳ cho loại sản phẩm Thành phẩm/Hàng hóa đích \ntrước khi hoàn thành tính giá cuối kỳ cho loại sản phẩm Thành phẩm/Hàng hóa nguồn')

    def prepare_value(self, product_id, line, type=None):
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
        vals = {}
        if type == 'source':
            account_credit = line.account_id.id if line.amount_diff > 0 else product_id.categ_id.property_stock_valuation_account_id.id
            account_debit = product_id.categ_id.property_stock_valuation_account_id.id if line.amount_diff > 0 else line.account_id.id
        else:
            account_debit = line.account_id.id if line.amount_diff > 0 else product_id.categ_id.property_stock_valuation_account_id.id
            account_credit = product_id.categ_id.property_stock_valuation_account_id.id if line.amount_diff > 0 else line.account_id.id

        lines = [
            (0, 0, {
                'name': self.name,
                'product_id': line.product_id.id if account_credit == line.account_id.id else product_id.id,
                'quantity': 0,
                'credit': line.amount_diff if line.amount_diff > 0 else -line.amount_diff,
                'account_id': account_credit,
                'work_order': line.production_code.id,
                'asset_id': line.asset_code.id,
                'occasion_code_id': line.occasion_code.id,
                'analytic_account_id': line.account_analytic.id,
            }),
            (0, 0, {
                'name': self.name,
                'product_id': line.product_id.id if account_debit == line.account_id.id else product_id.id,
                'quantity': 0,
                'debit': line.amount_diff if line.amount_diff > 0 else -line.amount_diff,
                'account_id': account_debit,
                'work_order': line.production_code.id,
                'asset_id': line.asset_code.id,
                'occasion_code_id': line.occasion_code.id,
                'analytic_account_id': line.account_analytic.id,
            }),

        ]

        vals.update({
            'date': self.to_date,
            'ref': self.name,
            'journal_id': journal_up_id.id if line.amount_diff > 0 else journal_down_id.id,
            'auto_post': 'no',
            'x_root': 'other',
            'end_period_entry': True,
            'is_change_price': True if type == 'source' else False,
            'line_ids': lines,
            'move_type': 'entry',
            'stock_valuation_layer_ids': [(0, 0, {
                'value': line.amount_diff,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'description': self.name,
                'product_id': product_id.id,
                'company_id': self.env.company.id
            })]
        })
        return vals

    def prepare_value_by_diff(self):
        vals = []
        for line in self.goods_diff_lines:
            vals.append(self.prepare_value(line.product_id, line, 'source'))
            if line.product_end_id:
                vals.append(self.prepare_value(line.product_end_id, line, 'end'))
        return vals

    def create_invoice_diff_entry(self):
        if self.state not in ('step2', 'step3'):
            raise ValidationError('Bản chỉ có thể thực hiện khi đã hoàn thành bảng kê chênh lệch')
        self.entry_ids.stock_valuation_layer_ids.unlink()
        self.entry_ids.unlink()

        move_vals = self.prepare_value_by_diff()
        moves = self.env['account.move'].create(move_vals)
        self.write({
            'entry_ids': [(6, 0, moves.ids)],
            'state': 'step3'
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': 'Tạo bút toán chênh lệch thành công!.',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    # cập nhật lại giá vốn
    def update_standard_price(self):
        for svl in self.entry_ids.stock_valuation_layer_ids:
            self.env['stock.move'].update_standard_price_product(svl.product_id)
        self.state = 'step4'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': 'Cập nhật giá vốn thành công!.',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_view_entry(self):
        self.ensure_one()
        move_ids = self.entry_ids.ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False},
            "name": _("Bút toán chênh lệch sản phẩm nguồn"),
            'view_mode': 'tree,form',
        }
        return result
