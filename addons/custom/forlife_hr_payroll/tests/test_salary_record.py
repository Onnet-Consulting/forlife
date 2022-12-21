# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import file_open
import base64


class TestSalaryRecord(TransactionCase):
    def setUp(self):
        super(TestSalaryRecord, self).setUp()

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
        self.accounting_manager = self.env['res.users'].create({
            'name': 'Accounting Test',
            'login': 'login_accounting_test',
            'groups_id': [(4, self.env.ref('account.group_account_manager').id)],
        })

        self.env['salary.record.type'].create({
            'code': '0',
            'name': 'Sản xuất',
        })

        self.env['salary.record.purpose'].create({
            'code': '64112022546',
            'name': 'Chi phí bán hàng',
        })
        self.env['salary.record.purpose'].create({
            'code': '64212022546',
            'name': 'Chi phí quản lý doanh nghiệp',
        })

        self.department = self.env['hr.department'].create({
            'code': 'TESTFM015',
            'name': 'TEST FORMAT THÁI HÀ',
        })
        self.department = self.env['hr.department'].create({
            'code': 'TESTPH001',
            'name': 'Phòng Hành Chính tổng hợp',
        })

        self.employee = self.env['hr.employee'].create({
            'barcode': 'test107759',
            'name': 'TEST Lưu Việt Dũng',
        })
        self.employee = self.env['hr.employee'].create({
            'barcode': 'test107882',
            'name': 'TEST Nguyễn Thị Vân Anh',
        })

        default_plan = self.env['account.analytic.plan'].create({'name': 'Default', 'company_id': False})
        self.env['account.analytic.account'].create({
            'name': 'Test Account1',
            'code': 'test1401100415',
            'plan_id': default_plan.id,
        })
        self.env['account.analytic.account'].create({
            'name': 'Test Account2',
            'code': 'test1401100409',
            'plan_id': default_plan.id,
        })

        with file_open('forlife_hr_payroll/tests/data/test_import_salary_record_success.xlsx', 'rb') as f:
            import_file = f.read()
            self.import_record_success = self.env['import.salary.record'].create({
                'import_file': base64.b64encode(import_file).decode('UTF-8'),
                'import_file_name': 'test_import_salary_record_success.xlsx',
            })
            self.import_record_2 = self.env['import.salary.record'].create({
                'import_file': base64.b64encode(import_file).decode('UTF-8'),
                'import_file_name': 'test_import_salary_record_success.xlsx',
            })
            self.import_record_3 = self.env['import.salary.record'].create({
                'import_file': base64.b64encode(import_file).decode('UTF-8'),
                'import_file_name': 'test_import_salary_record_success.xlsx',
            })
        with file_open('forlife_hr_payroll/tests/data/test_import_salary_record_fail.xlsx', 'rb') as f:
            import_file = f.read()
            self.import_record_fail = self.env['import.salary.record'].create({
                'import_file': base64.b64encode(import_file).decode('UTF-8'),
                'import_file_name': 'test_import_salary_record_fail.xlsx',
            })

    def test_import_salary_record_success(self):
        res = dict(self.import_record_success.action_import())
        self.assertEqual(res.get('res_model'), 'salary.record', res.get('name'))

    def test_import_salary_record_fail(self):
        res = dict(self.import_record_fail.action_import())
        self.assertEqual(res.get('res_model'), 'error.log.wizard', res.get('name'))

    def test_btn_confirm(self):
        res = dict(self.import_record_success.action_import())
        if res.get('res_model') == 'salary.record':
            salary_record = self.env['salary.record'].search([('id', '=', res.get('res_id'))])
            if not salary_record:
                self.assertEqual(salary_record.state, 'waiting', 'Salary Record not found with ID = "%s"' % res.get('res_id'))
            else:
                salary_record.with_user(self.payroll_employee).btn_confirm()
                self.assertEqual(salary_record.state, 'confirm', "Salary Record state is %s" % salary_record.state)
        else:
            self.assertEqual(res.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_btn_approved(self):
        res = dict(self.import_record_success.action_import())
        if res.get('res_model') == 'salary.record':
            salary_record = self.env['salary.record'].search([('id', '=', res.get('res_id'))])
            if not salary_record:
                self.assertEqual(salary_record.state, 'waiting', 'Salary Record not found with ID = "%s"' % res.get('res_id'))
            else:
                salary_record.with_user(self.payroll_employee).btn_confirm()
                salary_record.with_user(self.payroll_leader).btn_approved()
                self.assertEqual(salary_record.state, 'approved', "Salary Record state is %s" % salary_record.state)
        else:
            self.assertEqual(res.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_btn_cancel_after_confirm(self):
        res = dict(self.import_record_success.action_import())
        if res.get('res_model') == 'salary.record':
            salary_record = self.env['salary.record'].search([('id', '=', res.get('res_id'))])
            if not salary_record:
                self.assertEqual(salary_record.state, 'waiting', 'Salary Record not found with ID = "%s"' % res.get('res_id'))
            else:
                salary_record.with_user(self.payroll_employee).btn_confirm()
                salary_record.with_user(self.payroll_employee).btn_cancel()
                self.assertEqual(salary_record.state, 'cancel', "Salary Record state is %s" % salary_record.state)
        else:
            self.assertEqual(res.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_btn_cancel_after_approved(self):
        res = dict(self.import_record_success.action_import())
        if res.get('res_model') == 'salary.record':
            salary_record = self.env['salary.record'].search([('id', '=', res.get('res_id'))])
            if not salary_record:
                self.assertEqual(salary_record.state, 'waiting', 'Salary Record not found with ID = "%s"' % res.get('res_id'))
            else:
                salary_record.with_user(self.payroll_employee).btn_confirm()
                salary_record.with_user(self.payroll_leader).btn_approved()
                salary_record.with_user(self.payroll_employee).btn_cancel()
                self.assertEqual(salary_record.state, 'cancel', "Salary Record state is %s" % salary_record.state)
        else:
            self.assertEqual(res.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_btn_post(self):
        res = dict(self.import_record_success.action_import())
        if res.get('res_model') == 'salary.record':
            salary_record = self.env['salary.record'].search([('id', '=', res.get('res_id'))])
            if not salary_record:
                self.assertEqual(salary_record.state, 'waiting', 'Salary Record not found with ID = "%s"' % res.get('res_id'))
            else:
                salary_record.with_user(self.payroll_employee).btn_confirm()
                salary_record.with_user(self.payroll_leader).btn_approved()
                salary_record.with_user(self.accounting_manager).btn_post()
                self.assertEqual(salary_record.state, 'posted', "Salary Record state is %s" % salary_record.state)
        else:
            self.assertEqual(res.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_btn_cancel_post(self):
        res = dict(self.import_record_success.action_import())
        if res.get('res_model') == 'salary.record':
            salary_record = self.env['salary.record'].search([('id', '=', res.get('res_id'))])
            if not salary_record:
                self.assertEqual(salary_record.state, 'waiting', 'Salary Record not found with ID = "%s"' % res.get('res_id'))
            else:
                salary_record.with_user(self.payroll_employee).btn_confirm()
                salary_record.with_user(self.payroll_leader).btn_approved()
                salary_record.with_user(self.accounting_manager).btn_post()
                salary_record.with_user(self.accounting_manager).btn_cancel_post()
                self.assertEqual(salary_record.state, 'cancel_post', "Salary Record state is %s" % salary_record.state)
        else:
            self.assertEqual(res.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_import_after_previous_version_approved_or_posted(self):
        res = dict(self.import_record_success.action_import())
        if res.get('res_model') == 'salary.record':
            salary_record = self.env['salary.record'].search([('id', '=', res.get('res_id'))])
            if not salary_record:
                self.assertEqual(salary_record.state, 'waiting', 'Salary Record not found with ID = "%s"' % res.get('res_id'))
            else:
                salary_record.btn_confirm()
                salary_record.btn_approved()
                with self.assertRaises(ValidationError):
                    self.import_record_2.action_import()
        else:
            self.assertEqual(res.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_check_state_when_next_version_confirmed(self):
        res1 = dict(self.import_record_success.action_import())
        res2 = dict(self.import_record_2.action_import())
        res3 = dict(self.import_record_3.action_import())
        if res1.get('res_model') == 'salary.record' and res2.get('res_model') == 'salary.record':
            salary_record1 = self.env['salary.record'].search([('id', '=', res1.get('res_id'))])
            salary_record2 = self.env['salary.record'].search([('id', '=', res2.get('res_id'))])
            salary_record3 = self.env['salary.record'].search([('id', '=', res3.get('res_id'))])
            if not salary_record1 or not salary_record2 or not salary_record3:
                self.assertEqual(salary_record1.state, 'waiting', 'Salary Record not found with ID = "%s"' % res1.get('res_id'))
                self.assertEqual(salary_record2.state, 'waiting', 'Salary Record not found with ID = "%s"' % res2.get('res_id'))
                self.assertEqual(salary_record3.state, 'waiting', 'Salary Record not found with ID = "%s"' % res3.get('res_id'))
            else:
                salary_record2.btn_confirm()
                self.assertEqual(salary_record1.state, 'cancel', "Salary Record state is %s" % salary_record1.state)
                self.assertEqual(salary_record3.state, 'cancel', "Salary Record state is %s" % salary_record3.state)
        else:
            self.assertEqual(res1.get('res_model'), 'salary.record', 'Can not create Salary Record !')
            self.assertEqual(res2.get('res_model'), 'salary.record', 'Can not create Salary Record !')
            self.assertEqual(res3.get('res_model'), 'salary.record', 'Can not create Salary Record !')

    def test_import_salary_record_with_account_payroll_employee(self):
        self.import_record_success.with_user(self.payroll_employee).action_import()

    def test_import_salary_record_with_account_payroll_leader(self):
        with self.assertRaises(AccessError):
            self.import_record_success.with_user(self.payroll_leader).action_import()

    def test_import_salary_record_with_account_accounting(self):
        with self.assertRaises(AccessError):
            self.import_record_success.with_user(self.accounting_manager).action_import()
