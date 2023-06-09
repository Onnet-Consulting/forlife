import pytz
from odoo import models, fields, api, _
from datetime import datetime
from ..tools import convert_to_utc_datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


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

    @api.depends('period_start', 'period_end')
    def _compute_name(self):
        for rec in self:
            rec.name = _('Stock Balance Difference Report %s - %s') % (rec.period_start.strftime('%d/%m/%Y'), rec.period_end.strftime('%d/%m/%Y'))

    def _create_account_move(self):
        moves = self.env['account.move'].create([{
            'date': self.period_end,
            'ref': self.name,
            'line_ids': [
                (0, 0, {
                    'name': self.name,
                    'product_id': line.product_id,
                    'quantity': 0,
                    'credit': line.difference if line.difference > 0 else -line.difference,
                    'account_id': self.account_id.id if line.difference > 0 else line.account_id
                }),
                (0, 0, {
                    'name': self.name,
                    'product_id': line.product_id,
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
        } for line in self.line_ids if line.difference != 0])
        moves._post()

    def _generate_details(self, period_start, period_end):
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
                    sum(aml.debit) - sum(aml.credit) difference
                FROM account_move_line aml 
                JOIN product_product pp on pp.id = aml.product_id 
                JOIN product_template pt on pt.id = pp.product_tmpl_id
                JOIN ir_property ip on ip.res_id = 'product.category,' || pt.categ_id AND ip."name" = 'property_stock_valuation_account_id' AND ip.company_id = %s
                JOIN account_account aa on 'account.account,' || aa.id = ip.value_reference
                WHERE aml.company_id = %s AND aml.account_id = %s AND aml.product_id IS NOT NULL AND aml.date BETWEEN %s AND %s
                GROUP BY pp.id, aa.id
                ORDER BY pp.id
            ''',
            params=(
                self._context.get('lang') or 'en_US',
                self.env.company.id,
                self.env.company.id,
                self.account_id.id,
                period_start,
                period_end
            )
        )
        return self._cr.dictfetchall()

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
        } for line in self.line_ids]).ids)]

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
        self.line_ids = None
        self.account_move_ids = None
        self.line_ids = [(0, 0, line) for line in results if int(line['difference']) != 0]


class StockBalanceDifferenceReportLine(models.TransientModel):
    _name = 'stock.balance.difference.report.line'
    _description = 'Stock Balance Difference Report Line'

    product_id = fields.Integer(string='Product ID', required=True)
    product_code = fields.Char(string='Product Code')
    product_name = fields.Char(string='Product')
    account_id = fields.Integer(string='Stock Valuation Account ID')
    account_code = fields.Char(string='Stock Valuation Account')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    difference = fields.Float(string='Difference')
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

