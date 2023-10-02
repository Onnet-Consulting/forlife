import pytz
from odoo import models, fields, api, _
from datetime import datetime
from ..tools import convert_to_utc_datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError


class StockBalanceDifferenceReport(models.TransientModel):
    _name = 'stock.balance.difference.report'
    _description = 'Stock Balance Difference Report'

    name = fields.Char(compute='_compute_name', store=True)
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    account_id = fields.Many2one(comodel_name='account.account', string='Account', required=True, domain=lambda r: [('company_id', '=',  r.env.company.id)])
    line_ids = fields.One2many(comodel_name='stock.balance.difference.report.line', inverse_name='report_id')
    account_move_ids = fields.One2many(comodel_name='stock.balance.difference.report.account.move', inverse_name='report_id')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    purchase_order_ids = fields.Many2many('purchase.order', string='Đơn hàng', copy=False)

    @api.depends('period_start', 'period_end')
    def _compute_name(self):
        for rec in self:
            rec.name = _('Stock Balance Difference Report %s - %s') % (rec.period_start.strftime('%d/%m/%Y'), rec.period_end.strftime('%d/%m/%Y'))

    def _create_account_move(self):
        journal_id = self.env['account.journal'].search([('code', '=', 'ST01'), ('type', '=', 'general'), ('company_id', '=', self.company_id.id)], limit=1)
        moves = self.env['account.move'].create([{
            'date': self.period_end,
            'ref': self.name,
            'journal_id': journal_id.id or False,
            'auto_post': 'no',
            'x_root': 'other',
            'line_ids': [
                (0, 0, {
                    'name': self.name,
                    'product_id': line.product_id,
                    'purchase_line_id': line.purchase_line_id.id,
                    'quantity': 0,
                    'credit': line.difference if line.difference > 0 else -line.difference,
                    'account_id': self.account_id.id if line.difference > 0 else line.account_id
                }),
                (0, 0, {
                    'name': self.name,
                    'product_id': line.product_id,
                    'purchase_line_id': line.purchase_line_id.id,
                    'quantity': 0,
                    'debit': line.difference if line.difference > 0 else -line.difference,
                    'account_id': line.account_id if line.difference > 0 else self.account_id.id
                }),
            ],
            'move_type': 'entry',
            'stock_valuation_layer_ids': [(0, 0, {
                'value': line.difference if line.difference > 0 else -line.difference,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'description': self.name,
                'product_id': line.product_id,
                'company_id': self.env.company.id
            })]
        } for line in self.line_ids.filtered(lambda x: x.account_id) if line.difference != 0])
        moves.action_post()
        self.line_ids.unlink()

    def _generate_details(self, period_start, period_end):
        lang = self._context.get('lang') or 'en_US'
        company_id = self.env.company.id
        account_id = self.account_id.id

        if not self.purchase_order_ids:
            self._cr.execute(
                query='''
                    SELECT 
                        pp.id product_id, 
                        aa.id account_id,
                        max(pp.default_code) product_code, 
                        (ARRAY_AGG(pt.name))[1]::json->%s product_name, 
                        max(aa.code) account_code, 
                        sum(aml.debit) debit, 
                        sum(aml.credit) credit, 
                        sum(aml.debit) - sum(aml.credit) difference,
                        CASE WHEN sum(aml.debit) != 0 THEN (sum(aml.debit) - sum(aml.credit)) * 100/sum(aml.debit) ELSE 0 END difference_percent
                    FROM account_move_line aml 
                    JOIN product_product pp on pp.id = aml.product_id 
                    JOIN product_template pt on pt.id = pp.product_tmpl_id
                    JOIN ir_property ip on ip.res_id = 'product.category,' || pt.categ_id AND ip."name" = 'property_stock_valuation_account_id' AND ip.company_id = %s
                    JOIN account_account aa on 'account.account,' || aa.id = ip.value_reference
                    WHERE aml.company_id = %s AND aml.account_id = %s AND aml.product_id IS NOT NULL AND aml.date BETWEEN %s AND %s
                    GROUP BY pp.id, aa.id
                    ORDER BY pp.id
                ''',
                params=(lang, company_id, company_id, account_id, period_start, period_end)
            )
            return self._cr.dictfetchall()
        else:
            self._cr.execute(
                query='''
                    SELECT 
                        pp.id product_id, 
                        aa.id account_id,
                        max(pp.default_code) product_code, 
                        (ARRAY_AGG(pt.name))[1]::json->%s product_name, 
                        max(aa.code) account_code, 
                        0 debit, 
                        abs(sum(aml.balance)) credit,
                        pol.order_id purchase_id,
                        pol.id purchase_line_id
                    FROM account_move_line aml
                    JOIN account_move am on aml.move_id = am.id
                    JOIN stock_move sm on sm.id = am.stock_move_id 
                    JOIN purchase_order_line pol on sm.purchase_line_id = pol.id
                    JOIN product_product pp on pp.id = aml.product_id 
                    JOIN product_template pt on pt.id = pp.product_tmpl_id
                    JOIN ir_property ip on ip.res_id = 'product.category,' || pt.categ_id AND ip."name" = 'property_stock_valuation_account_id' AND ip.company_id = %s
                    JOIN account_account aa on 'account.account,' || aa.id = ip.value_reference
                    WHERE am.company_id = %s 
                        AND aml.account_id = %s 
                        AND aml.product_id IS NOT NULL
                        AND pol.order_id in %s
                        AND am.state = 'posted'
                    GROUP BY pp.id, aa.id, pol.order_id, pol.id
                    ORDER BY pol.order_id, pp.id
                ''',
                params=(lang, company_id, company_id, account_id, tuple(self.purchase_order_ids.ids))
            )

            inventory_datas = self._cr.dictfetchall()

            self._cr.execute(
                query='''
                    SELECT 
                        pp.id product_id, 
                        aa.id account_id,
                        max(pp.default_code) product_code, 
                        (ARRAY_AGG(pt.name))[1]::json->%s product_name, 
                        max(aa.code) account_code, 
                        sum(aml.balance) debit, 
                        0 credit,
                        pol.order_id purchase_id,
                        pol.id purchase_line_id
                    FROM account_move_line aml 
                    JOIN purchase_order_line pol on aml.purchase_line_id = pol.id
                    JOIN product_product pp on pp.id = aml.product_id 
                    JOIN product_template pt on pt.id = pp.product_tmpl_id
                    JOIN ir_property ip on ip.res_id = 'product.category,' || pt.categ_id AND ip."name" = 'property_stock_valuation_account_id' AND ip.company_id = %s
                    JOIN account_account aa on 'account.account,' || aa.id = ip.value_reference
                    WHERE aml.company_id = %s 
                        AND aml.account_id = %s 
                        AND aml.product_id IS NOT NULL 
                        AND pol.order_id in %s
                        AND aml.parent_state = 'posted'
                    GROUP BY pp.id, aa.id, pol.order_id, pol.id
                    ORDER BY pol.order_id, pp.id
                ''',
                params=(lang, company_id, company_id, account_id, tuple(self.purchase_order_ids.ids))
            )

            invoice_datas = self._cr.dictfetchall()

            data = []
            if inventory_datas != []:
                for inventory_line in inventory_datas:
                    vals = inventory_line
                    debit = 0
                    for invoice_line in invoice_datas:
                        if invoice_line.get('purchase_id') == vals.get('purchase_id') and invoice_line.get('purchase_id'):
                            debit += invoice_line.get('debit')
                    if vals.get('credit') != debit:
                        difference = debit - vals.get('credit')
                        vals.update({
                            'debit': debit,
                            'difference': difference,
                            'difference_percent': difference * 100/debit if debit != 0 else 0,
                        })
                        data.append(vals)
            else:
                for invoice_line in invoice_datas:
                    if invoice_line.get('debit'):
                        vals = invoice_line
                        vals.update({
                            'difference': invoice_line.get('debit'),
                            'difference_percent': 100,
                        })
                        data.append(vals)
            return data

    def create_account_move(self):
        self.generate_details()
        self._create_account_move()
        self.account_move_ids = [(6, 0, self.env['stock.balance.difference.report.account.move'].create([{
            'product_id': line.product_id,
            'product_code': line.product_code,
            'product_name': line.product_name,
            'debit_account_id': line.account_id if line.difference > 0 else self.account_id.id,
            'debit_account_code': line.account_code if line.difference > 0 else self.account_id.code,
            'credit_account_id': self.account_id.id if line.difference > 0 else line.account_id,
            'credit_account_code': self.account_id.code if line.difference > 0 else line.account_code,
            'amount_total': line.difference,
        } for line in self.line_ids.filtered(lambda x: x.account_id)]).ids)]

    def generate_details(self):
        current_tz = pytz.timezone(self._context.get('tz'))
        period_start = convert_to_utc_datetime(
            current_tz=current_tz,
            str_datetime=datetime(
                self.period_start.year,
                self.period_start.month,
                self.period_start.day
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        )
        period_end = convert_to_utc_datetime(
            current_tz=current_tz,
            str_datetime=datetime(
                self.period_end.year,
                self.period_end.month,
                self.period_end.day,
                23, 59, 59
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        )
        results = self._generate_details(period_start, period_end)
        if not results:
            raise ValidationError("Không có bút toán chênh lệch")
        self.line_ids = None
        self.account_move_ids = None
        if not self.purchase_order_ids:
            self.line_ids = [(0, 0, line) for line in results if int(line['difference']) != 0]
        else:
            po_names = { purchase.id: purchase.name for purchase in self.purchase_order_ids }
            line_vals = []
            total_debit = 0
            total_credit = 0
            purchase_id = None
            index = 1
            for line in results:
                if not purchase_id:
                    purchase_id = line.get('purchase_id')
                    total_debit += line.get('debit')
                    total_credit += line.get('credit')
                    line_vals.append((0, 0, line))
                    if index == len(results):
                        # Thêm line tổng
                        line_vals.append((0, 0, {
                            'product_name': 'Cong ' + po_names.get(purchase_id),
                            'debit': total_debit,
                            'credit': total_credit,
                            'difference': total_debit - total_credit,
                        }))
                else:
                    if line.get('purchase_id') == purchase_id:
                        total_debit += line.get('debit')
                        total_credit += line.get('credit')
                        line_vals.append((0, 0, line))

                        if index == len(results):
                            # Thêm line tổng
                            line_vals.append((0, 0, {
                                'product_name': 'Cong ' + po_names.get(purchase_id),
                                'debit': total_debit,
                                'credit': total_credit,
                                'difference': total_debit - total_credit,
                            }))
                    else:
                        # Thêm line tổng
                        line_vals.append((0, 0, {
                            'product_name': 'Cong ' +  po_names.get(purchase_id),
                            'debit': total_debit,
                            'credit': total_credit,
                            'difference': total_debit - total_credit,
                        }))

                        # Reset lại giá trị tổng và PO
                        line_vals.append((0, 0, line))
                        if index == len(results):
                            # Thêm line tổng
                            line_vals.append((0, 0, {
                                'product_name': 'Cong ' +  po_names.get(line.get('purchase_id')),
                                'debit': line.get('debit'),
                                'credit': line.get('credit'),
                                'difference': line.get('debit') - line.get('credit'),
                            }))
                        else:
                            purchase_id = line.get('purchase_id')
                            total_debit = line.get('debit')
                            total_credit = line.get('credit')
                index += 1
            self.line_ids = line_vals


class StockBalanceDifferenceReportLine(models.TransientModel):
    _name = 'stock.balance.difference.report.line'
    _description = 'Stock Balance Difference Report Line'

    product_id = fields.Integer(string='Product ID')
    product_code = fields.Char(string='Product Code')
    product_name = fields.Char(string='Product')
    account_id = fields.Integer(string='Stock Valuation Account ID')
    account_code = fields.Char(string='Stock Valuation Account')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    difference = fields.Float(string='Difference')
    difference_percent = fields.Float(string='% Chênh lệch')
    purchase_id = fields.Many2one(comodel_name='purchase.order', string='PO', ondelete='cascade')
    purchase_line_id = fields.Many2one(comodel_name='purchase.order.line', string='PO line', ondelete='cascade')
    report_id = fields.Many2one(comodel_name='stock.balance.difference.report', ondelete='cascade')


class StockBalanceDifferenceReportAccountMove(models.TransientModel):
    _name = 'stock.balance.difference.report.account.move'
    _description = 'Stock Balance Difference Report Account Move'

    product_id = fields.Integer(string='Product ID', required=True)
    product_code = fields.Char(string='Product Code')
    product_name = fields.Char(string='Product')
    debit_account_id = fields.Integer(string='Debit Account ID')
    debit_account_code = fields.Char(string='Debit Account')
    credit_account_id = fields.Integer(string='Credit Account ID')
    credit_account_code = fields.Char(string='Credit Account')
    amount_total = fields.Float(string='Amount Total')
    report_id = fields.Many2one(comodel_name='stock.balance.difference.report', ondelete='cascade')

