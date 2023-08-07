# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class SyntheticDailyTransfer(models.Model):
    _name = 'synthetic.daily.transfer'
    _description = 'Synthetic daily transfer'
    _rec_name = 'date'
    _order = 'date desc, id desc'

    date = fields.Date('Ngày', default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    line_ids = fields.One2many('synthetic.daily.transfer.location', 'synthetic_id', string='Chi tiết điều chuyển')

    @api.model
    def synchronize_daily_transfer(self, **kwargs):
        date = (kwargs.get('date') and datetime.strptime(kwargs.get('date'), '%d/%m/%Y')) or fields.Datetime.now()
        begin_date = (date + timedelta(days=-1)).replace(hour=17, second=0, minute=0)
        end_date = date.replace(hour=17, second=0, minute=0)
        domain = [
            ('state', '=', 'done'),
            ('transfer_id', '!=', False),
            # ('transfer_id.exists_bkav', '=', False),
            # ('other_export', '=', False),
            # ('other_import', '=', False),
            # ('date_done', '>', begin_date),
            # ('date_done', '<=', end_date),
        ]
        companies = self.env['res.company'].search([('code', '!=', False)])
        for company in companies:
            dm = domain + [('company_id', '=', company.id)]
            picking_count = self.env['stock.picking'].search_count(dm)
            if picking_count > 0:
                self._action_synthetic(company, dm, date.strftime('%Y-%m-%d'))

    @api.model
    def _action_synthetic(self, company, domain, date):
        pickings = self.env['stock.picking'].search(domain)
        source_is_deposit = pickings.filtered(lambda f: f.location_id.id_deposit and not f.location_dest_id.id_deposit)
        dest_is_deposit = pickings.filtered(lambda f: not f.location_id.id_deposit and f.location_dest_id.id_deposit)
        other_picking = pickings - source_is_deposit - dest_is_deposit
        for picking in source_is_deposit:
            pass
        self.sudo().create({
            'date': date,
            'company_id': company.id,
        })



class SyntheticDailyTransferLocation(models.Model):
    _name = 'synthetic.daily.transfer.location'
    _description = 'Synthetic daily transfer'
    _order = 'synthetic_id desc, id desc'

    synthetic_id = fields.Many2one('synthetic.daily.transfer', 'Phiếu tổng hợp', ondelete='restrict')
    location_id = fields.Many2one('stock.location', 'Địa điểm nguồn')
    location_dest_id = fields.Many2one('stock.location', 'Địa điểm đích')
    company_code = fields.Char('Công ty')
    transfer_code = fields.Char('Mã phiếu')
    description = fields.Char('Diễn giải')
    employee = fields.Char('Nhân viên nhập phiếu')
    source_warehouse = fields.Char('Kho xuất')
    destination_warehouse = fields.Char('Kho nhập')
    detail_ids = fields.One2many('synthetic.daily.transfer.line', 'sdt_location_id', string='Chi tiết sản phẩm')

    @api.model_create_multi
    def create(self, values):
        Sequence = self.env['ir.sequence']
        if not isinstance(values, list):
            values = [values]
        for val in values:
            year = self.env['synthetic.daily.transfer'].browse(val.get('synthetic_id')).date.year or fields.Date.today().year
            code = f"PTH-{val.get('source_warehouse') or ''}-{year}"
            transfer_code = False
            while not transfer_code:
                transfer_code = Sequence.next_by_code(code)
                if not transfer_code:
                    Sequence.create({
                        'name': code,
                        'code': code,
                        'prefix': f"PTH{val.get('source_warehouse') or ''}{int(year / 100 % 1 * 100)}",
                        'padding': 6,
                        'company_id': False,
                        'implementation': 'no_gap',
                    })
                    transfer_code = Sequence.next_by_code(code)
            val['transfer_code'] = transfer_code
        return super().create(values)


class SyntheticDailyTransferLine(models.Model):
    _name = 'synthetic.daily.transfer.line'
    _description = 'Synthetic daily transfer detail'
    _order = 'sdt_location_id desc, id desc'

    sdt_location_id = fields.Many2one('synthetic.daily.transfer.location', 'Điều chuyển', ondelete='restrict')
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    product_code = fields.Char('Mã sản phẩm')
    product_name = fields.Char('Tên sản phẩm')
    product_uom = fields.Char('Đơn vị tính')
    debit_account = fields.Char('Tài khoản nợ')
    credit_account = fields.Char('Tài khoản có')
    qty = fields.Float('Số lượng nhập')
    price = fields.Float('Đơn giá')
    amount_total = fields.Float('Thành tiền')
    occasion_code = fields.Char('Mã vụ việc')
    account_analytic = fields.Char('Mã trung tâm chi phí')
    work_production = fields.Char('Lệnh sản xuất')
    ma_xd_co_ban = fields.Char('Mã xây dựng cơ bản')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
