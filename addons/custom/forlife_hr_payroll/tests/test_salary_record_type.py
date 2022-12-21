# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


class TestSalaryRecordType(TransactionCase):
    def setUp(self):
        super(TestSalaryRecordType, self).setUp()

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

        self.salary_record_type = self.env['salary.record.type'].create({
            'code': 'employee0',
            'name': 'Purpose Test',
        })

    def test_create_salary_record_type_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.env['salary.record.type'].with_user(self.payroll_employee).create({
                'code': 'employee',
                'name': 'Type Test',
            })

    def test_create_salary_record_type_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.env['salary.record.type'].with_user(self.payroll_leader).create({
                'code': 'leader',
                'name': 'Type Test',
            })

    def test_write_salary_record_type_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_record_type.with_user(self.payroll_employee).write({
                'name': 'Type XXX',
            })

    def test_write_salary_record_type_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_record_type.with_user(self.payroll_leader).write({
                'name': 'Type XXX',
            })

    def test_delete_salary_record_type_with_account_employee(self):
        with self.assertRaises(AccessError):
            self.salary_record_type.with_user(self.payroll_employee).unlink()

    def test_delete_salary_record_type_with_account_leader(self):
        with self.assertRaises(AccessError):
            self.salary_record_type.with_user(self.payroll_leader).unlink()
