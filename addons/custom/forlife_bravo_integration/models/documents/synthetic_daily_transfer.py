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
    _inherit = 'bravo.model.insert.action'
    _bravo_table = 'B30AccDocInventory'

    date = fields.Date('Ngày', default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    queue_job_id = fields.Many2one('queue.job', 'Queue job')
    state = fields.Selection(related='queue_job_id.state', string='Trạng thái đồng bộ Bravo')
    message = fields.Text(related='queue_job_id.exc_info', string='Thông báo')
    line_ids = fields.One2many('synthetic.daily.transfer.location', 'synthetic_id', string='Chi tiết điều chuyển')

    @api.model
    def synchronize_daily_transfer(self, **kwargs):
        date = (kwargs.get('date') and datetime.strptime(kwargs.get('date'), '%d/%m/%Y')) or fields.Datetime.now()
        begin_date = (date + timedelta(days=-1)).replace(hour=17, second=0, minute=0)
        end_date = date.replace(hour=17, second=0, minute=0)
        domain = [
            ('state', '=', 'done'),
            ('transfer_id', '!=', False),
            ('transfer_id.exists_bkav', '=', False),
            ('other_export', '=', False),
            ('other_import', '=', False),
            ('date_done', '>=', begin_date),
            ('date_done', '<', end_date),
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
        line_ids = self.prepare_data('source', 'Thu hồi hàng ký gửi', source_is_deposit, company) if source_is_deposit else []
        line_ids.extend(self.prepare_data('dest', 'Xuất hàng ký gửi', dest_is_deposit, company) if dest_is_deposit else [])
        line_ids.extend(self.prepare_data('other', 'Xuất điều chuyển nội bộ', other_picking, company) if other_picking else [])
        if line_ids:
            result = self.sudo().create([{
                'date': date,
                'company_id': company.id,
                'line_ids': line_ids,
            }])
            if self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
                result.action_sync_by_queue()

    def action_sync_by_queue(self):
        self.ensure_one()
        queries = self.bravo_get_insert_sql()
        if queries:
            uuid = self.with_company(self.company_id).with_delay(
                description=f"Đồng bộ: Tổng hợp điều chuyển ngày {self.date.strftime('%d-%m-%Y')}", channel="root.Bravo").bravo_execute_query(queries).uuid
            queue_job_id = self.env['queue.job'].search([('uuid', '=', uuid)], limit=1)
            if queue_job_id:
                self.sudo().write({'queue_job_id': queue_job_id.id})

    @api.model
    def prepare_data(self, type, description, pickings, company):
        if not pickings:
            return []
        data = []
        for picking in pickings:
            val = {
                'source_warehouse': picking.location_id.warehouse_id.code or '',
                'destination_warehouse': picking.location_dest_id.warehouse_id.code or '',
            }
            for stock_move in picking.move_ids:
                account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
                credit_line = account_move.line_ids.filtered(lambda l: l.credit > 0)
                credit = int(credit_line[0].credit) if credit_line else 0
                if type == 'source':
                    price = int(credit / stock_move.quantity_done) if stock_move.quantity_done else 0
                    amount_total = credit
                    debit_account = stock_move.product_id.categ_id.with_company(company).property_stock_valuation_account_id.code or ''
                    credit_account = picking.location_dest_id.account_stock_give.code or ''
                elif type == 'dest':
                    price = int(credit / stock_move.quantity_done) if stock_move.quantity_done else 0
                    amount_total = credit
                    debit_account = picking.location_id.account_stock_give.code or ''
                    credit_account = stock_move.product_id.categ_id.with_company(company).property_stock_valuation_account_id.code or ''
                else:
                    price = 0
                    amount_total = 0
                    debit_account = stock_move.product_id.categ_id.with_company(company).property_stock_valuation_account_id.code or ''
                    credit_account = stock_move.product_id.categ_id.with_company(company).property_stock_valuation_account_id.code or ''
                val.update({
                    'product_code': stock_move.product_id.barcode or '',
                    'product_name': stock_move.product_id.name or '',
                    'product_uom': stock_move.product_id.uom_id.code or '',
                    'debit_account': debit_account,
                    'credit_account': credit_account,
                    'qty': stock_move.quantity_done,
                    'price': price,
                    'amount_total': amount_total,
                    'occasion_code': stock_move.occasion_code_id.code or '',
                    'account_analytic': stock_move.account_analytic_id.code or '',
                    'work_production': stock_move.work_production.code or '',
                })
                data.append(val)
        key_getter1 = itemgetter('source_warehouse', 'destination_warehouse')
        value_getter1 = itemgetter('product_code', 'product_name', 'product_uom', 'debit_account', 'credit_account',
                                   'qty', 'price', 'amount_total', 'occasion_code', 'account_analytic', 'work_production')
        key_getter2 = itemgetter('product_code', 'product_name', 'product_uom', 'debit_account', 'credit_account',
                                 'occasion_code', 'account_analytic', 'work_production', 'price')
        value_getter2 = itemgetter('qty', 'amount_total')
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
                qty, amount_total = zip(*map(value_getter2, objs2))
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
                    'amount_total': sum(amount_total) or 0,
                }))
            result1.append((0, 0, {
                'source_warehouse': source_wh,
                'destination_warehouse': destination_wh,
                'company_code': company.code,
                'description': description,
                'detail_ids': result2,
            }))
        return result1

    @api.model
    def bravo_get_default_insert_value(self):
        return {}

    def bravo_get_insert_values(self, **kwargs):
        bravo_column_names = [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "Description",
            "EmployeeCode", "DeptCode", "IsTransfer", "ReceiptWarehouseCode", "PushDate", "BuiltinOrder",
            "CreditAccount", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9", "Quantity",
            "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount", "WarehouseCode", "JobCode", "RowId", "DocNo_WO",
        ]
        values = []
        builtin_order = 1
        for transfer_wh in self.line_ids:
            row_id = 1
            for detail in transfer_wh.detail_ids:
                values.append({
                    "CompanyCode": transfer_wh.company_code or None,
                    "Stt": transfer_wh.transfer_code or None,
                    "DocCode": "DC",
                    "DocNo": transfer_wh.transfer_code or None,
                    "DocDate": self.date.strftime('%Y-%m-%d 07:00:00') if self.date else None,
                    "CurrencyCode": self.company_id.currency_id.name or None,
                    "ExchangeRate": 1,
                    "Description": transfer_wh.description or None,
                    "IsTransfer": 0,
                    "ReceiptWarehouseCode": transfer_wh.destination_warehouse or None,
                    "PushDate": self.date.strftime('%Y-%m-%d 07:00:00') if self.date else None,
                    "BuiltinOrder": builtin_order,
                    "CreditAccount": detail.credit_account or None,
                    "ItemCode": detail.product_code or None,
                    "ItemName": detail.product_name or None,
                    "UnitPurCode": detail.product_uom or None,
                    "DebitAccount": detail.debit_account or None,
                    "Quantity9": detail.qty or 0,
                    "ConvertRate9": 1,
                    "Quantity": detail.qty or 0,
                    "OriginalUnitCost": detail.price or 0,
                    "UnitCost": detail.price or 0,
                    "OriginalAmount": detail.amount_total or 0,
                    "Amount": detail.amount_total or 0,
                    "WarehouseCode": transfer_wh.source_warehouse or None,
                    "JobCode": detail.occasion_code or None,
                    "RowId": row_id,
                    "DocNo_WO": detail.work_production or None,
                    'DeptCode': detail.account_analytic or None,
                })
                row_id += 1
            builtin_order += 1
        return bravo_column_names, values


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


class AccountingInventoryDifferenceWizard(models.TransientModel):
    _name = 'acc.inv.diff.wizard'
    _description = 'Đồng bộ hạch toán chênh lệch kiểm kê'
    _inherit = 'bravo.model.insert.action'

    @api.model
    def synchronize_accounting_inventory_difference(self, **kwargs):
        date = (kwargs.get('date') and datetime.strptime(kwargs.get('date'), '%d/%m/%Y')) or fields.Datetime.now()
        begin_date = (date + timedelta(days=-1)).replace(hour=17, second=0, minute=0)
        end_date = date.replace(hour=17, second=0, minute=0)
        domain = [
            '|', '&', '&',
            ('date_confirm1', '>=', begin_date),
            ('date_confirm1', '<', end_date),
            ('move_in_count1', '!=', 0),
            '&', '&',
            ('date_confirm2', '>=', begin_date),
            ('date_confirm2', '<', end_date),
            ('move_in_count', '!=', 0),
        ]
        companies = self.env['res.company'].search([('code', '!=', False)])
        for company in companies:
            dm = domain + [('company_id', '=', company.id)]
            inv_count = self.env['stock.inventory'].search_count(dm)
            if inv_count > 0:
                self._action_synchronize(dm, begin_date, end_date, date.strftime('%Y-%m-%d 07:00:00'))

    @api.model
    def _action_synchronize(self, domain, begin_date, end_date, date):
        inventories = self.env['stock.inventory'].search(domain)
        for inv in inventories:
            sync_number = inv.sync_number
            if inv.date_confirm1 and inv.date_confirm1 >= begin_date and inv.date_confirm1 < end_date:
                move_out1 = inv.move_ids.filtered(lambda x: x.state == 'done' and x.location_id.id == inv.location_id.id and x.inv_state == 'first_inv')
                sync_number = self.sync_move(inv, move_out1, 'out', sync_number, 'xuất lần 1', date)
                move_in1 = inv.move_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.id == inv.location_id.id and x.inv_state == 'first_inv')
                sync_number = self.sync_move(inv, move_in1, 'in', sync_number, 'nhập lần 1', date)
            if inv.date_confirm2 and inv.date_confirm2 >= begin_date and inv.date_confirm2 < end_date:
                move_out2 = inv.move_ids.filtered(lambda x: x.state == 'done' and x.location_id.id == inv.location_id.id and x.inv_state == 'second_inv')
                sync_number = self.sync_move(inv, move_out2, 'out', sync_number, 'xuất lần 2', date)
                move_in2 = inv.move_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.id == inv.location_id.id and x.inv_state == 'second_inv')
                sync_number = self.sync_move(inv, move_in2, 'in', sync_number, 'nhập  lần 2', date)
            if sync_number > inv.sync_number:
                inv.sudo().write({'sync_number': sync_number})

    @api.model
    def bravo_get_table(self, **kwargs):
        return 'B30AccDocItemReceipt' if kwargs.get('move_type') == 'in' else 'B30AccDocItemIssue'

    @api.model
    def bravo_get_default_insert_value(self):
        return {}

    @api.model
    def bravo_get_insert_values(self, **kwargs):
        bravo_column_names = [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "DocumentType", "PushDate",
            "BuiltinOrder", "CreditAccount", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9",
            "ConvertRate9", "Quantity", "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount",
            "WarehouseCode", "JobCode", "RowId", "DocNo_WO", "DeptCode", "ExpenseCatgCode",
        ]
        values = []
        inventory = kwargs.get('inventory')
        company = inventory.company_id
        sync_number = kwargs.get('sync_number')
        date = kwargs.get('date')
        move_type = kwargs.get('move_type')
        for stock_move in (kwargs.get('move_ids') or []):
            if move_type == 'in':
                doc_code = "PN"
                description = 'Nhập kho theo phiếu kiểm kê'
                document_type = 'N0202'
                account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
                credit_line = account_move.line_ids.filtered(lambda l: l.credit > 0)
                credit_account = credit_line.account_id.code or self.env['stock.location'].search([
                    ('company_id', '=', company.id), ('code', '=', 'N0202'), ('type_other', '!=', False)]).with_company(company).x_property_valuation_out_account_id.code or None
                credit = int(credit_line[0].credit) if credit_line else 0
                debit_line = account_move.line_ids.filtered(lambda l: l.debit > 0)
                debit_account = debit_line.account_id.code or stock_move.product_id.categ_id.with_company(company).property_stock_valuation_account_id.code or None
                debit = int(debit_line[0].debit) if debit_line else 0
                wh_code = 1
                amount = debit or credit
            else:
                doc_code = 'PX'
                description = 'Xuất kho theo phiếu kiểm kê'
                document_type = 'X0202'
                account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
                credit_line = account_move.line_ids.filtered(lambda l: l.credit > 0)
                credit_account = credit_line.account_id.code or stock_move.product_id.categ_id.with_company(company).property_stock_valuation_account_id.code or None
                credit = int(credit_line[0].credit) if credit_line else 0
                debit_line = account_move.line_ids.filtered(lambda l: l.debit > 0)
                debit_account = debit_line.account_id.code or self.env['stock.location'].search([
                    ('company_id', '=', company.id), ('code', '=', 'X0202'), ('type_other', '!=', False)]).with_company(company).x_property_valuation_out_account_id.code or None
                debit = int(debit_line[0].debit) if debit_line else 0
                wh_code = 2
                amount = debit or credit

            values.append({
                "CompanyCode": company.code or None,
                "Stt": inventory.name[1:] + ('%.2d' % sync_number) or None,
                "DocCode": doc_code,
                "DocNo": inventory.name[1:] + ('%.2d' % sync_number) or None,
                "DocDate": date or None,
                "CurrencyCode": company.currency_id.name or None,
                "ExchangeRate": 1,
                "CustomerCode": None,
                "CustomerName": None,
                "Address": None,
                "Description": description,
                "EmployeeCode": inventory.create_uid.employee_id.code or None,
                "IsTransfer": 0,
                "DocumentType": document_type,
                "PushDate": date or None,
                "BuiltinOrder": 1,
                "CreditAccount": credit_account or None,
                "ItemCode": stock_move.product_id.barcode or None,
                "ItemName": stock_move.product_id.name or None,
                "UnitPurCode": stock_move.product_id.uom_id.code or None,
                "DebitAccount": debit_account or None,
                "Quantity9": stock_move.quantity_done or 0,
                "ConvertRate9": 1,
                "Quantity": stock_move.quantity_done or 0,
                "OriginalUnitCost": stock_move.quantity_done if amount / stock_move.quantity_done else 0,
                "UnitCost": stock_move.quantity_done if amount / stock_move.quantity_done else 0,
                "OriginalAmount": amount,
                "Amount": amount,
                "WarehouseCode": wh_code or None,
                "JobCode": stock_move.occasion_code_id.code or None,
                "RowId": 1,
                "DocNo_WO": stock_move.work_production.code or None,
                'DeptCode': stock_move.account_analytic_id.code or None,
                'ExpenseCatgCode': None,
            })
        return bravo_column_names, values

    @api.model
    def sync_move(self, inventory, move_ids, move_type, sync_number, lan_kk, date):
        while move_ids:
            _move_ids = move_ids[:1000]
            queries = self.bravo_get_insert_sql(inventory=inventory, move_type=move_type, move_ids=_move_ids, sync_number=sync_number, date=date)
            if queries:
                self.with_company(inventory.company_id).with_delay(description=f"Đồng bộ: Hạch toán chênh lệch kiểm kê {lan_kk}", channel="root.Bravo").bravo_execute_query(queries)
            move_ids = move_ids - _move_ids
            sync_number += 1
        return sync_number
