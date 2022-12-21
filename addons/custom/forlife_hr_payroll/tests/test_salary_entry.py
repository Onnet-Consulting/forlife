# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


class TestSalaryEntry(TransactionCase):
    def setUp(self):
        super(TestSalaryEntry, self).setUp()

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

        model1_id = self.env['ir.model'].search([('model', '=', 'salary.record.main')], limit=1)
        field1_id = self.env['ir.model.fields'].search([('model_id', '=', model1_id.id)], limit=1)

        self.model2_id = self.env['ir.model'].search([('model', '=', 'salary.total.income')], limit=1)
        self.field2_id = self.env['ir.model.fields'].search([('model_id', '=', self.model2_id.id)], limit=1)

        self.salary_entry = self.env['salary.entry'].create({
            'salary_table_id': model1_id.id,
            'salary_field_id': field1_id.id,
            'title': 'Title Test 0',
        })

    def test_create_salary_entry_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.env['salary.entry'].with_user(self.payroll_employee).create({
                'salary_table_id': self.model2_id.id,
                'salary_field_id': self.field2_id.id,
                'title': 'Title Test',
            })

    def test_create_salary_entry_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.env['salary.entry'].with_user(self.payroll_leader).create({
                'salary_table_id': self.model2_id.id,
                'salary_field_id': self.field2_id.id,
                'title': 'Title Test',
            })

    def test_write_salary_entry_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_entry.with_user(self.payroll_employee).write({
                'title': 'Title XXX',
            })

    def test_write_salary_entry_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_entry.with_user(self.payroll_leader).write({
                'title': 'Title XXX',
            })

    def test_delete_salary_entry_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_entry.with_user(self.payroll_employee).unlink()

    def test_delete_salary_entry_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_entry.with_user(self.payroll_leader).unlink()
