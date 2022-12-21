# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


class TestSalaryRecordPurpose(TransactionCase):
    def setUp(self):
        super(TestSalaryRecordPurpose, self).setUp()

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

        self.salary_record_purpose = self.env['salary.record.purpose'].create({
            'code': 'code01',
            'name': 'Purpose Test',
        })

    def test_create_salary_record_purpose_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.env['salary.record.purpose'].with_user(self.payroll_employee).create({
                'code': 'employee',
                'name': 'Purpose Test',
            })

    def test_create_salary_record_purpose_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.env['salary.record.purpose'].with_user(self.payroll_leader).create({
                'code': 'leader',
                'name': 'Purpose Test',
            })

    def test_write_salary_record_purpose_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_record_purpose.with_user(self.payroll_employee).write({
                'name': 'Purpose XXX',
            })

    def test_write_salary_record_purpose_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_record_purpose.with_user(self.payroll_leader).write({
                'name': 'Purpose XXX',
            })

    def test_delete_salary_record_purpose_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_record_purpose.with_user(self.payroll_employee).unlink()

    def test_delete_salary_record_purpose_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_record_purpose.with_user(self.payroll_leader).unlink()
