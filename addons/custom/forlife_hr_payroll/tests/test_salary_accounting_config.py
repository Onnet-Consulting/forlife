# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


class TestSalaryAccountingConfig(TransactionCase):
    def setUp(self):
        super(TestSalaryAccountingConfig, self).setUp()

        self.payroll_employee = self.env['res.users'].create({
            'name': 'Employee Test',
            'login': 'login_employee_test',
            'groups_id': [(4, self.env.ref('forlife_hr_payroll.payroll_employee').id)],
        })

        self.payroll_leader = self.env['res.users'].create({
            'name': 'Leader Test',
            'login': 'login_leader_test',
            'groups_id': [(4, self.env.ref('forlife_hr_payroll.payroll_leader').id)],
        })

        self.debit_account_id = self.env['account.account'].create({
            'name': 'Test Account',
            'account_type': 'liability_payable',
            'code': 'TestDebitAccount',
            'reconcile': True,
        })

        self.credit_account_id = self.env['account.account'].create({
            'name': 'Test Account',
            'account_type': 'asset_receivable',
            'code': 'TestCreditAccount',
            'reconcile': True,
        })

        self.partner1_id = self.env['res.partner'].create({
            'name': 'Test Partner 1',
        })

        self.partner2_id = self.env['res.partner'].create({
            'name': 'Test Partner 2',
        })

        model1_id = self.env['ir.model'].search([('model', '=', 'salary.record.main')], limit=1)
        field1_id = self.env['ir.model.fields'].search([('model_id', '=', model1_id.id)], limit=1)

        entry1_id = self.env['salary.entry'].create({
            'salary_table_id': model1_id.id,
            'salary_field_id': field1_id.id,
            'title': 'Title Test 0',
        })
        purpose1_id = self.env['salary.record.purpose'].create({
            'code': 'code01',
            'name': 'Purpose Test',
        })

        model2_id = self.env['ir.model'].search([('model', '=', 'salary.total.income')], limit=1)
        field2_id = self.env['ir.model.fields'].search([('model_id', '=', model2_id.id)], limit=1)

        self.entry2_id = self.env['salary.entry'].create({
            'salary_table_id': model2_id.id,
            'salary_field_id': field2_id.id,
            'title': 'Title Test 0',
        })

        self.purpose2_id = self.env['salary.record.purpose'].create({
            'code': 'code02',
            'name': 'Purpose Test',
        })

        self.salary_accounting_config = self.env['salary.accounting.config'].create({
            'entry_id': entry1_id.id,
            'purpose_id': purpose1_id.id,
            'debit_account_id': self.debit_account_id.id,
            'credit_account_id': self.credit_account_id.id,
            'debit_partner_id': self.partner1_id.id,
            'credit_partner_id': self.partner2_id.id,
        })

    def test_create_salary_accounting_config_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.env['salary.accounting.config'].with_user(self.payroll_employee).create({
                'entry_id': self.entry2_id.id,
                'purpose_id': self.purpose2_id.id,
                'debit_account_id': self.debit_account_id.id,
                'credit_account_id': self.credit_account_id.id,
                'debit_partner_id': self.partner1_id.id,
                'credit_partner_id': self.partner2_id.id,
            })

    def test_create_salary_accounting_config_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.env['salary.accounting.config'].with_user(self.payroll_leader).create({
                'entry_id': self.entry2_id.id,
                'purpose_id': self.purpose2_id.id,
                'debit_account_id': self.debit_account_id.id,
                'credit_account_id': self.credit_account_id.id,
                'debit_partner_id': self.partner1_id.id,
                'credit_partner_id': self.partner2_id.id,
            })

    def test_write_salary_accounting_config_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_accounting_config.with_user(self.payroll_employee).write({
                'debit_partner_id': self.partner2_id.id,
            })

    def test_write_salary_accounting_config_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_accounting_config.with_user(self.payroll_leader).write({
                'debit_partner_id': self.partner2_id.id,
            })

    def test_delete_salary_accounting_config_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_accounting_config.with_user(self.payroll_employee).unlink()

    def test_delete_salary_accounting_config_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_accounting_config.with_user(self.payroll_leader).unlink()
