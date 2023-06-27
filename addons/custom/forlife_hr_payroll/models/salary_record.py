# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import date_utils
from odoo.exceptions import ValidationError

MONTH_SELECTION = [
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7'),
    ('8', '8'),
    ('9', '9'),
    ('10', '10'),
    ('11', '11'),
    ('12', '12'),
]


class SalaryRecord(models.Model):
    _name = 'salary.record'
    _description = 'Salary Record'

    @api.model
    def _get_years(self):
        year_list = []
        from_year = datetime.now() - relativedelta(years=10)
        to_year = datetime.now() + relativedelta(years=5)
        for i in range(from_year.year, to_year.year):
            year_list.append((str(i), str(i)))
        return year_list

    name = fields.Char(string='Name', required=True, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    type_id = fields.Many2one('salary.record.type', string='Type', required=True, ondelete='restrict')
    month = fields.Selection(MONTH_SELECTION, string='Month', required=True)
    year = fields.Selection(_get_years, string='Year', required=True)
    version = fields.Integer(string='Version', default=1)
    state = fields.Selection(
        [('waiting', 'Waiting'), ('confirm', 'Confirm'), ('approved', 'Approved'), ('cancel', 'Cancelled'),
         ('posted', 'Posted'), ('cancel_post', 'Cancelled Posting')],
        string='State', default='waiting', required=True)
    confirm_date = fields.Date(string='Confirmation Date (HR)')
    confirm_user = fields.Many2one('res.users', string='Confirmation User (HR)', ondelete="restrict")
    confirm_date_accounting = fields.Date(string='Confirmation Date (ACC)')
    confirm_user_accounting = fields.Many2one('res.users', string='Confirmation User (ACC)', ondelete="restrict")
    note = fields.Text(string='Description')
    cancel_date = fields.Date(string='Cancel Date')
    cancel_user = fields.Many2one('res.users', string='Cancel User')

    salary_record_main_ids = fields.One2many('salary.record.main', 'salary_record_id', 'Salary Record Main')
    salary_total_income_ids = fields.One2many('salary.total.income', 'salary_record_id', 'Salary Total Income')
    salary_supplementary_ids = fields.One2many('salary.supplementary', 'salary_record_id', 'Salary Supplementary')
    salary_arrears_ids = fields.One2many('salary.arrears', 'salary_record_id', 'Salary Arrears')
    salary_accounting_ids = fields.One2many('salary.accounting', 'salary_record_id', 'Salary Accounting')
    salary_backlog_ids = fields.One2many('salary.backlog', 'salary_record_id', 'Salary Backlog')
    move_ids = fields.One2many('account.move', 'salary_record_id', string='Account Moves', copy=False, readonly=False)
    move_count = fields.Integer(compute='_compute_move_count')

    _sql_constraints = [
        ('unique_combination', 'UNIQUE(company_id, type_id, month, year, version)',
         'The combination of Company, Type, Month, Year and Version must be unique !')
    ]

    @api.depends('move_ids')
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.move_ids)

    def action_view_journals(self):
        self.ensure_one()
        invoices = self.mapped('move_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'general',
        }
        action['context'] = context
        return action

    def action_view_group_accounting(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('forlife_hr_payroll.action_view_accounting')
        action['domain'] = [('salary_record_id', '=', self.id)]
        return action

    def action_view_change_Log(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('forlife_hr_payroll.save_change_log_action')
        action['domain'] = [('record', '=', '%s,%r' % (self._name, self.id))]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for value in vals_list:
            company = self.env['res.company'].browse(value.get('company_id')) or self.env.company
            value['name'] = company.salary_record_sequence_id.next_by_id()
            next_version = self.search_count([
                ('company_id', '=', company.id), ('type_id', '=', value.get('type_id')),
                ('month', '=', value.get('month')), ('year', '=', value.get('year'))
            ]) + 1
            value['version'] = next_version
        return super(SalaryRecord, self).create(vals_list)

    @api.model
    def create_salary_record_sequence(self):
        companies = self.env['res.company'].search([]).filtered(lambda rec: not rec.salary_record_sequence_id)
        ir_sequence = self.env['ir.sequence']
        for company in companies:
            sequence = ir_sequence.create({
                'name': 'Salary Record Sequence',
                'prefix': (company.code or '') + '-',
                'padding': 6,
                'company_id': company.id,
                'implementation': 'no_gap',
            })
            company.write({
                'salary_record_sequence_id': sequence.id
            })

    def btn_confirm(self):
        rec = self.filtered(lambda x: x.state == 'waiting')
        rec.sudo().write({
            'state': 'confirm',
            'confirm_date': datetime.now(),
            'confirm_user': self.env.uid,
        })
        self.env['save.change.log'].create_log(records=rec, message=_('Confirm'))
        for line in rec:
            self.search([
                ('company_id', '=', line.company_id.id), ('type_id', '=', line.type_id.id), ('month', '=', line.month),
                ('year', '=', line.year), ('state', 'in', ('waiting', 'confirm')), ('version', '!=', line.version)
            ]).btn_cancel()

    def btn_approved(self):
        rec = self.filtered(lambda x: x.state == 'confirm')
        rec.sudo().write({
            'state': 'approved',
            'confirm_date': datetime.now(),
            'confirm_user': self.env.uid,
        })
        self.env['save.change.log'].create_log(records=rec, message=_('Approved'))

    def btn_cancel(self):
        rec = self.filtered(lambda x: x.state in ('waiting', 'approved', 'confirm'))
        rec.sudo().write({
            'state': 'cancel',
            'cancel_date': datetime.now(),
            'cancel_user': self.env.uid,
        })
        self.env['save.change.log'].create_log(records=rec, message=_('Cancelled'))

    def btn_post(self):
        self.ensure_one()
        if self.state != 'approved':
            return False
        self._active_employee_partners()
        self.generate_account_moves()

        self.sudo().write({
            'state': 'posted',
            'confirm_date_accounting': datetime.now(),
            'confirm_user_accounting': self.env.uid,
        })

        self.env['save.change.log'].create_log(records=self, message=_('Posted'))

    def get_accounting_date(self):
        start_of_month = datetime.strptime('%s-%s-01' % (self.year, self.month), DF).date()
        end_of_month = date_utils.end_of(start_of_month, 'month')
        return end_of_month

    def _active_employee_partners(self):
        self.ensure_one()
        self.salary_arrears_ids.mapped('employee_id'). \
            mapped('partner_id').filtered(lambda p: not p.active).write({'active': True})
        return True

    def group_accounting_data_by_entry_and_account(self, accounting_values_by_entry):
        entry_ids = list(accounting_values_by_entry.keys())
        entries = self.env['salary.entry'].browse(entry_ids)

        for entry in entries:
            groupable_account_ids = entry.groupable_account_ids
            if not groupable_account_ids:
                continue
            new_entry_data = []
            group_data_by_account_and_partner = {}
            entry_id = entry.id
            groupable_account_ids = groupable_account_ids.ids
            for line_value in accounting_values_by_entry[entry_id]:
                account_id = line_value['account_id']
                if account_id not in groupable_account_ids:
                    new_entry_data.append(line_value)
                    continue
                partner_id = line_value['partner_id'] or 0
                group_key = '%r_%r' % (account_id, partner_id)
                if group_key not in group_data_by_account_and_partner:
                    group_data_by_account_and_partner[group_key] = {}
                    group_data_by_account_and_partner[group_key]['debit'] = line_value['debit']
                    group_data_by_account_and_partner[group_key]['credit'] = line_value['credit']
                else:
                    group_data_by_account_and_partner[group_key]['debit'] += line_value['debit']
                    group_data_by_account_and_partner[group_key]['credit'] += line_value['credit']
            for group_key, debit_credit_values in group_data_by_account_and_partner.items():
                account_id = int(group_key.split('_')[0])
                partner_id = int(group_key.split('_')[1]) or False
                total_debit = debit_credit_values['debit']
                total_credit = debit_credit_values['credit']
                if total_debit:
                    new_entry_data.append(
                        dict(partner_id=partner_id, account_id=account_id, debit=total_debit, credit=0))
                if total_credit:
                    new_entry_data.append(
                        dict(partner_id=partner_id, account_id=account_id, debit=0, credit=total_credit))
            if new_entry_data:
                accounting_values_by_entry[entry_id] = new_entry_data
        return accounting_values_by_entry

    def generate_account_moves(self):
        self.ensure_one()
        self.generate_account_move_with_tc_options_and_work_order(True, True)
        self.generate_account_move_with_tc_options_and_work_order(True, False)
        self.generate_account_move_with_tc_options_and_work_order(False, True)
        self.generate_account_move_with_tc_options_and_work_order(False, False)
        return True

    def generate_account_move_with_tc_options_and_work_order(self, is_tc_entry, has_work_order):
        salary_accounting_ids = self.salary_accounting_ids.filtered(
            lambda l: l.is_tc_entry == is_tc_entry and bool(l.production_id) == has_work_order)
        accounting_values_by_entry = {}
        accounting_line_by_entry = {}
        entry_by_id = {}
        default_journal_id = self.get_default_journal_id_for_salary_move()
        for line in salary_accounting_ids:
            line_value = dict(
                partner_id=line.partner_id.id,
                account_id=line.account_id.id,
                debit=line.debit,
                credit=line.credit,
                analytic_account_id=line.analytic_account_id.id,
                asset_id=line.asset_id.id,
                work_order=line.production_id.id,
                occasion_code_id=line.occasion_code_id.id,
                expense_item_id=line.expense_item_id.id
            )
            entry = line.entry_id
            entry_id = entry.id
            entry_by_id[entry_id] = entry
            if entry_id not in accounting_values_by_entry:
                accounting_values_by_entry[entry_id] = [line_value]
                accounting_line_by_entry[entry_id] = line
            else:
                accounting_values_by_entry[entry_id].append(line_value)
                accounting_line_by_entry[entry_id] |= line

        account_move = self.env['account.move']
        accounting_date = self.get_accounting_date()
        account_move_value = {
            'salary_record_id': self.id,
            'invoice_date': accounting_date,
            'narration': self.note,
            'ref': self.name,
            'x_asset_fin': 'TC' if is_tc_entry else 'QT',
            'journal_id': default_journal_id
        }

        accounting_values_by_entry = self.group_accounting_data_by_entry_and_account(accounting_values_by_entry)

        for entry_id, move_lines in accounting_values_by_entry.items():
            entry = entry_by_id[entry_id]
            move_value = account_move_value.copy()
            move_value.update({
                'ref2': entry.show_name,
                'line_ids': [(0, 0, line_value) for line_value in move_lines]
            })
            move = account_move.create(move_value)
            self.check_valid_salary_move(move)
            move.action_post()
            accounting_lines = accounting_line_by_entry[entry_id]
            accounting_lines.write({'move_id': move.id})
        return True

    def check_valid_salary_move(self, move):
        journal_lines = move.line_ids
        debit_lines = journal_lines.filtered(lambda l: l.debit > 0)
        credit_lines = journal_lines - debit_lines
        if len(debit_lines) > 1 and len(credit_lines) > 1:
            raise ValidationError(_("Bút toán không được phép nhiều nợ - nhiều có!"))

    def get_default_journal_id_for_salary_move(self):
        JOURNAL_CODE = '971'
        salary_journal = self.env['account.journal'].search([
            ('code', '=', JOURNAL_CODE),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not salary_journal:
            raise ValidationError(_("Không tìm thấy sổ nhật ký có mã %s") % JOURNAL_CODE)
        return salary_journal.id

    def reverse_account_moves(self):
        if not self.move_ids:
            return False

        accounting_date = self.get_accounting_date()
        move_reversal = self.env['account.move.reversal'].sudo().with_context(active_ids=self.move_ids.ids,
                                                                              active_model='account.move').create({
            'date_mode': 'custom',
            'move_ids': [(6, 0, self.move_ids.ids)],
            'journal_id': self.move_ids[0].journal_id.id,
            'date': accounting_date,
        })
        move_reversal.reverse_moves()
        reversed_moves = self.move_ids.filtered(lambda x: x.reversed_entry_id)
        for rev_move in reversed_moves:
            origin_move = rev_move.reversed_entry_id
            salary_accounting = self.salary_accounting_ids.filtered(lambda x: x.move_id == origin_move)
            salary_accounting.write({'reverse_move_id': rev_move.id})
        return True

    def btn_cancel_post(self):
        self.ensure_one()
        self.reverse_account_moves()
        if self.state != 'posted':
            return False
        self.sudo().write({
            'state': 'cancel_post',
            'cancel_date': datetime.now(),
            'cancel_user': self.env.uid,
        })

        self.env['save.change.log'].create_log(records=self, message=_('Cancelled Posting'))
