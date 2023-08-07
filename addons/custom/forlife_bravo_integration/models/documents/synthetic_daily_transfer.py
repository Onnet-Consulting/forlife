# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from itertools import groupby
from operator import itemgetter


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
        line_ids = self.prepare_data('source', 'Thu hồi hàng ký gửi', source_is_deposit, company, date) if source_is_deposit else []
        line_ids.extend(self.prepare_data('dest', 'Xuất hàng ký gửi', dest_is_deposit, company, date) if dest_is_deposit else [])
        line_ids.extend(self.prepare_data('other', 'Xuất điều chuyển nội bộ', other_picking, company, date) if other_picking else [])
        if line_ids:
            self.sudo().create({
                'date': date,
                'company_id': company.id,
                'line_ids': line_ids,
            })

    @api.model
    def prepare_data(self, type, description, pickings, company, date):
        if not pickings:
            return []
        data = []
        for picking in pickings:
            val = {
                'source_warehouse': picking.location_id.warehouse_id.code or '',
                'destination_warehouse': picking.location_dest_id.warehouse_id.code or '',
            }
            for stock_move in picking.move_ids:
                val.update({
                    'product_code': stock_move.product_id.barcode or '',
                    'product_name': stock_move.product_id.name or '',
                    'product_uom': stock_move.product_id.uom_id.code or '',
                    'debit_account': stock_move.product_id.categ_id.property_stock_valuation_account_id.code or '',
                    'credit_account': stock_move.product_id.categ_id.property_stock_valuation_account_id.code or '',
                    'qty': stock_move.quantity_done,
                    'price': 0,
                    'amount_total': 0,
                    'occasion_code': stock_move.occasion_code_id.code or '',
                    'account_analytic': stock_move.account_analytic_id.code or '',
                    'work_production': stock_move.work_production.code or '',
                })
                data.append(val)
        key_getter1 = itemgetter('source_warehouse', 'destination_warehouse')
        value_getter1 = itemgetter('product_code', 'product_name', 'product_uom', 'debit_account', 'credit_account', 'qty', 'price', 'amount_total', 'occasion_code', 'account_analytic', 'work_production')
        key_getter2 = itemgetter('product_code', 'product_name', 'product_uom', 'debit_account', 'credit_account', 'occasion_code', 'account_analytic', 'work_production', 'price', 'amount_total')
        value_getter2 = itemgetter('qty', 'qty')
        result1 = []
        for (source_wh, destination_wh), objs1 in groupby(sorted(data, key=key_getter1), key_getter1):
            vals1 = []
            v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11 = zip(*map(value_getter1, objs1))
            for idx, v in enumerate(v1):
                vals1.append({
                    'product_code': v1[idx],
                    'product_name': v2[idx],
                    'product_uom': v3[idx],
                    'debit_account': v4[idx],
                    'credit_account': v5[idx],
                    'qty': v6[idx],
                    'price': v7[idx],
                    'amount_total': v8[idx],
                    'occasion_code': v9[idx],
                    'account_analytic': v10[idx],
                    'work_production': v11[idx],
                })
            result2 = []
            for key, objs2 in groupby(sorted(vals1, key=key_getter2), key_getter2):
                qty, x = zip(*map(value_getter2, objs2))
                result2.append((0, 0, {
                    'product_code': key[0],
                    'product_name': key[1],
                    'product_uom': key[2],
                    'debit_account': key[3],
                    'credit_account': key[4],
                    'occasion_code': key[5],
                    'account_analytic': key[6],
                    'work_production': key[7],
                    'qty': sum(qty) or 0,
                    'price': key[8],
                    'amount_total': key[9],
                }))
            result1.append((0, 0, {
                'source_warehouse': source_wh,
                'destination_warehouse': destination_wh,
                'company_code': company.code,
                'description': description,
                'detail_ids': result2,
            }))
        return result1


class SyntheticDailyTransferLocation(models.Model):
    _name = 'synthetic.daily.transfer.location'
    _description = 'Synthetic daily transfer'
    _order = 'synthetic_id desc, id desc'

    synthetic_id = fields.Many2one('synthetic.daily.transfer', 'Phiếu tổng hợp', ondelete='restrict')
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
