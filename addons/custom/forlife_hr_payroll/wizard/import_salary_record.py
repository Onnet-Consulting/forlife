# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import xlrd
import base64
import re

MONTH = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12')


class ImportSalaryRecord(models.TransientModel):
    _name = 'import.salary.record'
    _description = 'Import Salary Record'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company,
                                 string='Company', readonly=True, store=True, required=True)
    import_file = fields.Binary(attachment=False, string='Upload file')
    import_file_name = fields.Char()

    def download_template_file(self):
        attachment_id = self.env.ref('forlife_hr_payroll.import_salary_record_data_file_sample')
        return {
            'type': 'ir.actions.act_url',
            'name': 'Import Salary Record Data',
            'url': 'web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=Template import TH số liệu lương.xlsx' % attachment_id.id,
            'target': 'new'
        }

    def action_import(self):
        has_error, data = self.read_file_data()
        if has_error:
            return self.env['error.log.wizard'].return_error_log(data)
        salary_record_id = self.insert_data(data)
        salary_record_action = self.env['ir.actions.act_window']._for_xml_id('forlife_hr_payroll.salary_record_action')
        salary_record_action.update({
            'res_id': salary_record_id,
            'target': 'main',
            'views': [(False, 'form')]
        })
        return salary_record_action

    @api.model
    def get_key_by_record(self, record):
        keys = [record.purpose_id.id, record.department_id.id, record.analytic_account_id.id, record.asset_id.id]
        keys = [str(x) for x in keys]
        return '_'.join(keys)

    def attach_remain_data_to_salary_main(self, salary_record):
        record_mains = {}
        for record in salary_record.salary_record_main_ids:
            key = self.get_key_by_record(record)
            record_mains[key] = record

        total_income_aggregations = {}
        supplementary_aggregations = {}
        arrears_aggregations = {}

        for income in salary_record.salary_total_income_ids:
            key = self.get_key_by_record(income)
            income_id = income.id
            if key in total_income_aggregations:
                total_income_aggregations[key].append(income_id)
            else:
                total_income_aggregations[key] = [income_id]

        for suppl in salary_record.salary_supplementary_ids:
            key = self.get_key_by_record(suppl)
            suppl_id = suppl.id
            if key in supplementary_aggregations:
                supplementary_aggregations[key].append(suppl_id)
            else:
                supplementary_aggregations[key] = [suppl_id]

        for arrears in salary_record.salary_arrears_ids:
            key = self.get_key_by_record(arrears)
            arrears_id = arrears.id
            if key in arrears_aggregations:
                arrears_aggregations[key].append(arrears_id)
            else:
                arrears_aggregations[key] = [arrears_id]

        for key, record_main in record_mains.items():
            values = {}
            if key in total_income_aggregations:
                values.update({
                    'total_income_ids': total_income_aggregations.get(key)
                })
            if key in supplementary_aggregations:
                values.update({
                    'supplementary_ids': supplementary_aggregations.get(key)
                })
            if key in arrears_aggregations:
                values.update({
                    'arrears_ids': arrears_aggregations.get(key)
                })
            record_main.write(values) if values else False

    def insert_data(self, data):
        salary_record = self.insert_header_data(data['header_data'])
        salary_record_id = salary_record.id
        self.insert_salary_total_income_data(data['salary_total_income_data'], salary_record_id)
        self.insert_salary_supplementary_data(data['salary_supplementary_data'], salary_record_id)
        self.insert_salary_arrears_data(data['salary_arrears_data'], salary_record_id)
        self.insert_salary_backlog_data(data['salary_backlog_data'], salary_record_id)
        self.insert_salary_main_data(data['salary_main_data'], salary_record_id)
        self.attach_remain_data_to_salary_main(salary_record)
        self.insert_salary_accounting_data(salary_record)
        return salary_record_id

    def insert_header_data(self, data):
        salary_record = self.env['salary.record'].create(data)
        return salary_record

    def insert_salary_main_data(self, data, salary_record_id):
        for main in data:
            main.update({'salary_record_id': salary_record_id})
        return self.env['salary.record.main'].create(data)

    def insert_salary_total_income_data(self, data, salary_record_id):
        for income in data:
            income.update({'salary_record_id': salary_record_id})
        return self.env['salary.total.income'].create(data)

    def insert_salary_supplementary_data(self, data, salary_record_id):
        for suppl in data:
            suppl.update({'salary_record_id': salary_record_id})
        return self.env['salary.supplementary'].create(data)

    def insert_salary_arrears_data(self, data, salary_record_id):
        for arrears in data:
            arrears.update({'salary_record_id': salary_record_id})
        return self.env['salary.arrears'].create(data)

    def insert_salary_backlog_data(self, data, salary_record_id):
        for backlog in data:
            backlog.update({'salary_record_id': salary_record_id})
        return self.env['salary.backlog'].create(data)

    def insert_salary_accounting_data(self, salary_record):
        entries = self.env['salary.entry'].sudo().search([])
        entry_salary_main = entries.filtered(lambda x: x.salary_table_id.model == 'salary.record.main')
        entry_total_income = entries.filtered(lambda x: x.salary_table_id.model == 'salary.total.income')
        entry_supplementary = entries.filtered(lambda x: x.salary_table_id.model == 'salary.supplementary')
        entry_arrears = entries.filtered(lambda x: x.salary_table_id.model == 'salary.arrears')

        accounting_configs = self.env['salary.accounting.config'].search([])
        salary_main_accounting_by_purpose_id = self.mapping_entry_with_accounting_config(entry_salary_main,
                                                                                         accounting_configs)
        total_income_accounting_by_purpose_id = self.mapping_entry_with_accounting_config(entry_total_income,
                                                                                          accounting_configs)
        supplementary_accounting_by_purpose_id = self.mapping_entry_with_accounting_config(entry_supplementary,
                                                                                           accounting_configs)
        arrears_accounting_by_purpose_id = self.mapping_entry_with_accounting_config(entry_arrears, accounting_configs)

        salary_record_id = salary_record.id
        salary_main_accounting_values = self.generate_accounting_value(salary_record.salary_record_main_ids,
                                                                       salary_main_accounting_by_purpose_id,
                                                                       'salary.record.main', salary_record_id)
        total_income_accounting_values = self.generate_accounting_value(salary_record.salary_total_income_ids,
                                                                        total_income_accounting_by_purpose_id,
                                                                        'salary.total.income', salary_record_id)
        supplementary_accounting_values = self.generate_accounting_value(salary_record.salary_supplementary_ids,
                                                                         supplementary_accounting_by_purpose_id,
                                                                         'salary.supplementary', salary_record_id)
        arrears_accounting_values = self.generate_accounting_value(salary_record.salary_arrears_ids,
                                                                   arrears_accounting_by_purpose_id,
                                                                   'salary.arrears', salary_record_id)

        accounting_values = salary_main_accounting_values + total_income_accounting_values \
                            + supplementary_accounting_values + arrears_accounting_values

        self.env['salary.accounting'].create(accounting_values)
        salary_record.salary_accounting_ids.filtered(lambda rec: rec.debit == 0 and rec.credit == 0).unlink()
        return True

    @api.model
    def mapping_entry_with_accounting_config(self, entries, accounting_config):
        # 1 salary purpose -> mapping with record line (main, total income ...) -> 2 accounting lines for each record line
        accounting_value_by_purpose_id = {}
        for entry in entries:
            for config in accounting_config:
                if config.entry_id != entry:
                    continue
                values = [
                    {'accounting_config_id': config.id, 'accounting_type': 'debit'},
                    {'accounting_config_id': config.id, 'accounting_type': 'credit'},
                ]

                purpose_id = config.purpose_id.id
                if purpose_id not in accounting_value_by_purpose_id:
                    accounting_value_by_purpose_id[purpose_id] = values
                else:
                    accounting_value_by_purpose_id[purpose_id].extend(values)
        return accounting_value_by_purpose_id

    @api.model
    def generate_accounting_value(self, records, accounting_value_by_purpose_id, record_model, salary_record_id):
        accounting_values = []
        for rec in records:
            record_purpose_id = rec.purpose_id.id
            for accounting_value in (accounting_value_by_purpose_id.get(record_purpose_id) or []):
                copy_accounting_value = accounting_value.copy()
                copy_accounting_value.update({
                    'record': '%s,%r' % (record_model, rec.id),
                    'salary_record_id': salary_record_id
                })
                accounting_values.append(copy_accounting_value)
        return accounting_values

    @api.model
    def get_purpose_code(self, purpose_name):
        match_code = re.match(r'^\d+', purpose_name)
        match_code = match_code.group(0) if match_code else False
        return match_code

    @api.model
    def get_type_code(self, type_name):
        match_code = re.match(r'^\d+', type_name)
        match_code = match_code.group(0) if match_code else 0
        return int(match_code)

    def map_purpose_data(self, data):
        purpose_codes = []
        for purpose in data:
            code = self.get_purpose_code(purpose)
            if code and code not in purpose_codes:
                purpose_codes.append(code)
        purposes = self.env['salary.record.purpose'].search([('code', 'in', purpose_codes)])

        purpose_by_code = {p.code: p.id for p in purposes}
        error_by_code = {}

        for purpose in data:
            code = self.get_purpose_code(purpose)
            if code and not purpose_by_code.get(code):
                error_message = 'Mục đích tính lương %s không tồn tại' % purpose
                error_by_code[code] = error_message
        return purpose_by_code, error_by_code

    def map_employee_data(self, data):
        if not data:
            return {}, {}
        employees = self.env['hr.employee'].search(
            ['&', '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id),
             '|', ('code', 'in', list(data.keys())), ('name', 'in', list(data.values()))])
        error_by_code = {}
        employee_by_code = {}
        employee_data_by_code = {epl.code: (epl.name, epl.id) for epl in employees}

        for import_code, import_name in data.items():
            db_data = employee_data_by_code.get(import_code)
            if not db_data or import_name != db_data[0]:
                error_by_code[import_code] = 'Tên-mã nhân viên không tồn tại hoặc không khớp: "%s" "%s"' % (import_name, import_code)
                continue
            employee_by_code[import_code] = db_data[1]

        return employee_by_code, error_by_code

    def map_department_data(self, data):
        departments = self.env['hr.department'].search(
            ['&', '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id),
             '|', ('code', 'in', list(data.keys())), ('name', 'in', list(data.values()))])
        error_by_code = {}
        department_by_code = {}
        department_data_by_code = {d.code: (d.name, d.id) for d in departments}

        for import_code, import_name in data.items():
            db_data = department_data_by_code.get(import_code)
            if not db_data or import_name != db_data[0]:
                error_by_code[import_code] = 'Tên-Mã phòng ban/bộ phận không tồn tại hoặc không khớp:  "%s" "%s"' % (import_name, import_code)
                continue
            department_by_code[import_code] = db_data[1]

        return department_by_code, error_by_code

    def map_analytic_data(self, data):
        analytic_accounts = self.env['account.analytic.account'].search([
            ('code', 'in', data),
            ('company_id', '=', self.company_id.id)])
        analytic_by_code = {a.code: a.id for a in analytic_accounts}
        error_by_code = {}
        for code in data:
            if code and not analytic_by_code.get(code):
                error_by_code[code] = 'Mã cost center %s không tồn tại' % code
        return analytic_by_code, error_by_code

    def map_project_data(self, data):
        assets_assets = self.env['assets.assets'].search(
            [('code', 'in', data), ('company_id', '=', self.company_id.id)]
        )
        asset_by_code = {a.code: a.id for a in assets_assets}
        error_by_code = {}
        for code in data:
            if code and not asset_by_code.get(code):
                error_by_code[code] = 'Mã dự án %s không tồn tại' % code
        return asset_by_code, error_by_code

    def map_manufacturing_data(self, data):
        productions = self.env['forlife.production'].search([
            ('code', 'in', data), ('company_id', '=', self.company_id.id)
        ])
        production_by_code = {p.code: p.id for p in productions}
        error_by_code = {}
        for code in data:
            if code and not production_by_code.get(code):
                error_by_code[code] = "Mã lệnh sản xuất %s không tồn tại" % code
        return production_by_code, error_by_code

    def map_internal_order_data(self, data):
        occasions = self.env['occasion.code'].search([
            ('code', 'in', data), ('company_id', '=', self.company_id.id)
        ])
        occasion_by_code = {oc.code: oc.id for oc in occasions}
        error_by_code = {}
        for code in data:
            if code and not occasion_by_code.get(code):
                error_by_code[code] = "Mã vụ việc %s không tồn tại" % code
        return occasion_by_code, error_by_code

    def map_data(self, **kwargs):
        """
        Mapping data between Excel file <-> Odoo
        :param kwargs: Contains dict value of data from xls, each pair of key-value is the value need to check in system Odoo
                     possible keys: ['purpose', 'employee', 'department', 'analytic', 'project', 'manufacturing', 'internal_order']
        :return: dict
        """
        res = {}
        self = self.sudo()
        for key in kwargs.keys():
            if not kwargs.get(key):
                res[key] = [{}, {}]
            else:
                res[key] = getattr(self, ''.join(['map_', key, '_data']))(kwargs.get(key))
        return res

    @api.model
    def generate_sheet_error_by_index(self, line_errors, workbook, sheet_index):
        sheet_name = workbook.sheet_by_index(sheet_index).name
        return '\n\n======\tSheet - %s\t========== \n%s\n' % (sheet_name, line_errors)

    @api.model
    def read_file_data(self):
        if not self.import_file:
            raise UserError(_("Please upload file template before click Import button !"))
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        header_data, error_header = self.read_header_data(workbook)
        salary_main_data, error_main = self.read_salary_main_data(workbook)
        salary_total_income_data, error_income = self.read_salary_total_income_data(workbook)
        salary_supplementary_data, error_supplementary = self.read_salary_supplementary_data(workbook)
        salary_arrears_data, error_arrears = self.read_salary_arrears_data(workbook)
        salary_backlog_data, error_backlog = self.read_salary_backlog_data(workbook)
        errors = [error_header, error_main, error_income, error_supplementary, error_arrears, error_backlog]
        error_message = ''
        for idx, line_errors in enumerate(errors):
            if line_errors:
                error_message += self.generate_sheet_error_by_index(line_errors, workbook, idx)
        if error_message:
            return True, error_message
        return False, {
            'header_data': header_data,
            'salary_main_data': salary_main_data,
            'salary_total_income_data': salary_total_income_data,
            'salary_supplementary_data': salary_supplementary_data,
            'salary_arrears_data': salary_arrears_data,
            'salary_backlog_data': salary_backlog_data,
        }

    @api.model
    def read_header_data(self, workbook, sheet_index=0):
        data = self.env['res.utility'].read_xls_book(workbook, sheet_index)
        data = [x for x in data]
        data = data[1:2]
        errors = ''
        xls_departments_name_and_code = {}
        for row_idx, row in enumerate(data):
            xls_departments_name_and_code.update({row[5]: row[6]})
        xls_data = dict(department=xls_departments_name_and_code)
        mapped_data = self.map_data(**xls_data)
        department_by_code, department_error_by_code = mapped_data.get('department')
        res = []
        for index, value in enumerate(data, start=2):
            type_code = self.get_type_code(value[0])
            year = value[1]
            month = value[2]
            is_tc = (value[4] or '').strip() == 'TC'
            department_code = value[5]

            salary_record_type = self.env['salary.record.type'].search([('code', '=', type_code)])
            try:
                year = str(int(year))
            except (TypeError, ValueError):
                year = False
            try:
                month = str(int(month))
            except (TypeError, ValueError):
                month = False

            errors += f"Dòng %r, Loại lương '%s' không hợp lệ\n" % (index, type_code) if not salary_record_type else ''
            errors += 'Dòng %r, năm %r không hợp lệ\n' % (index, year) if not year else ''
            errors += 'Dòng %r, tháng %r không hợp lệ\n' % (index, month) if month not in MONTH else ''

            department_error = department_error_by_code.get(department_code)
            if department_error:
                errors += f'Dòng {index}, {department_error}\n'
            if not errors:
                salary_record_exits = self.env['salary.record'].search([
                    ('company_id', '=', self.company_id.id), ('type_id', '=', salary_record_type.id),
                    ('month', '=', month), ('year', '=', year), ('state', 'in', ('approved', 'posted')),
                    ('is_tc', '=', is_tc), ('department_id', '=', department_by_code.get(department_code) or False)])
                if salary_record_exits:
                    message = _(
                        'Salary records could not be imported, some previous versions were approved or posted: %s') \
                              % ', '.join(salary_record_exits.mapped('name'))
                    raise ValidationError(message)
                res.append({
                    'type_id': salary_record_type.id,
                    'year': year,
                    'month': month,
                    'note': value[3],
                    'is_tc': is_tc,
                    'department_id': department_by_code.get(department_code),
                })
            else:
                res = []
        return res, errors

    @api.model
    def read_salary_main_data(self, workbook, sheet_index=1):
        data = self.env['res.utility'].read_xls_book(workbook, sheet_index)
        data = [x for x in data]
        start_row = 1
        data = data[start_row:]
        res = []
        errors = []
        xls_purposes = []
        xls_departments_name_and_code = {}
        xls_analytic_accounts = []
        xls_projects = []

        for row_idx, row in enumerate(data):
            xls_purposes.append(row[0])
            xls_departments_name_and_code.update({row[1]: row[2]})
            xls_analytic_accounts.append(row[3])
            xls_projects.append(row[4])
        xls_data = dict(purpose=xls_purposes, department=xls_departments_name_and_code, analytic=xls_analytic_accounts,
                        project=xls_projects)
        mapped_data = self.map_data(**xls_data)
        purpose_by_code, purpose_error_by_code = mapped_data.get('purpose')
        department_by_code, department_error_by_code = mapped_data.get('department')
        analytic_by_code, analytic_error_by_code = mapped_data.get('analytic')
        project_by_code, project_error_by_code = mapped_data.get('project')

        for row_idx, row in enumerate(data, start=start_row + 1):
            purpose_code = self.get_purpose_code(row[0])
            department_code = row[1]
            analytic_code = row[3]
            project_code = row[4]

            purpose_error = purpose_error_by_code.get(purpose_code)
            department_error = department_error_by_code.get(department_code)
            analytic_error = analytic_error_by_code.get(analytic_code)
            project_error = project_error_by_code.get(project_code)
            line_error = [purpose_error, department_error, analytic_error, project_error]
            line_error = list(filter(None, line_error))
            if line_error:
                line_error = ['Dòng %s, ' % row_idx + error for error in line_error]
                errors.append('\n'.join(line_error))
            else:
                value = {
                    'purpose_id': purpose_by_code.get(purpose_code),
                    'department_id': department_by_code.get(department_code),
                    'analytic_account_id': analytic_by_code.get(analytic_code),
                    'asset_id': project_by_code.get(project_code) or False,
                    'x_slns': float(row[5]) if row[5] else 0,
                }
                res.append(value)

        errors = '\n'.join(errors)
        return res, errors

    @api.model
    def read_salary_total_income_data(self, workbook, sheet_index=2):
        data = self.env['res.utility'].read_xls_book(workbook, sheet_index)
        data = [x for x in data]
        start_row = 1
        data = data[start_row:]
        res = []
        errors = []
        xls_purposes = []
        xls_departments_name_and_code = {}
        xls_analytic_accounts = []
        xls_projects = []
        xls_manufacturing = []
        xls_internal_orders = []

        for row_idx, row in enumerate(data):
            xls_purposes.append(row[0])
            xls_departments_name_and_code.update({row[1]: row[2]})
            xls_analytic_accounts.append(row[3])
            xls_projects.append(row[4])
            xls_manufacturing.append(row[5])
            xls_internal_orders.append(row[6])
        xls_data = dict(
            purpose=xls_purposes, department=xls_departments_name_and_code, analytic=xls_analytic_accounts,
            project=xls_projects, manufacturing=xls_manufacturing, internal_order=xls_internal_orders
        )
        mapped_data = self.map_data(**xls_data)
        purpose_by_code, purpose_error_by_code = mapped_data.get('purpose')
        department_by_code, department_error_by_code = mapped_data.get('department')
        analytic_by_code, analytic_error_by_code = mapped_data.get('analytic')
        project_by_code, project_error_by_code = mapped_data.get('project')
        manufacturing_by_code, manufacturing_error_by_code = mapped_data.get('manufacturing')
        internal_order_by_code, internal_order_error_by_code = mapped_data.get('internal_order')

        for row_idx, row in enumerate(data, start=start_row + 1):
            purpose_code = self.get_purpose_code(row[0])
            department_code = row[1]
            analytic_code = row[3]
            project_code = row[4]
            manufacturing_code = row[5]
            internal_order_code = row[6]

            purpose_error = purpose_error_by_code.get(purpose_code)
            department_error = department_error_by_code.get(department_code)
            analytic_error = analytic_error_by_code.get(analytic_code)
            project_error = project_error_by_code.get(project_code)
            manufacturing_error = manufacturing_error_by_code.get(manufacturing_code)
            internal_order_error = internal_order_error_by_code.get(internal_order_code)
            line_error = [purpose_error, department_error, analytic_error, project_error, manufacturing_error,
                          internal_order_error]
            line_error = list(filter(None, line_error))
            if line_error:
                line_error = ['Dòng %s, ' % row_idx + error for error in line_error]
                errors.append('\n'.join(line_error))
            else:
                value = {
                    'purpose_id': purpose_by_code.get(purpose_code),
                    'department_id': department_by_code.get(department_code),
                    'analytic_account_id': analytic_by_code.get(analytic_code),
                    'asset_id': project_by_code.get(project_code) or False,
                    'production_id': manufacturing_by_code.get(manufacturing_code) or False,
                    'occasion_code_id': internal_order_by_code.get(internal_order_code) or False,
                    'x_ttn': float(row[7]) if row[7] else 0,
                    'note': row[8],
                }
                res.append(value)
        errors = '\n'.join(errors)
        return res, errors

    @api.model
    def read_salary_supplementary_data(self, workbook, sheet_index=3):
        data = self.env['res.utility'].read_xls_book(workbook, sheet_index)
        data = [x for x in data]
        start_row = 1
        data = data[start_row:]
        res = []
        errors = []
        xls_purposes = []
        xls_departments_name_and_code = {}
        xls_analytic_accounts = []
        xls_projects = []
        xls_manufacturing = []
        xls_internal_orders = []

        for row_idx, row in enumerate(data):
            xls_purposes.append(row[0])
            xls_departments_name_and_code.update({row[1]: row[2]})
            xls_analytic_accounts.append(row[3])
            xls_projects.append(row[4])
            xls_manufacturing.append(row[5])
            xls_internal_orders.append(row[6])
        xls_data = dict(
            purpose=xls_purposes, department=xls_departments_name_and_code, analytic=xls_analytic_accounts,
            project=xls_projects, manufacturing=xls_manufacturing, internal_order=xls_internal_orders
        )
        mapped_data = self.map_data(**xls_data)
        purpose_by_code, purpose_error_by_code = mapped_data.get('purpose')
        department_by_code, department_error_by_code = mapped_data.get('department')
        analytic_by_code, analytic_error_by_code = mapped_data.get('analytic')
        project_by_code, project_error_by_code = mapped_data.get('project')
        manufacturing_by_code, manufacturing_error_by_code = mapped_data.get('manufacturing')
        internal_order_by_code, internal_order_error_by_code = mapped_data.get('internal_order')

        for row_idx, row in enumerate(data, start=start_row + 1):
            purpose_code = self.get_purpose_code(row[0])
            department_code = row[1]
            analytic_code = row[3]
            project_code = row[4]
            manufacturing_code = row[5]
            internal_order_code = row[6]

            purpose_error = purpose_error_by_code.get(purpose_code)
            department_error = department_error_by_code.get(department_code)
            analytic_error = analytic_error_by_code.get(analytic_code)
            project_error = project_error_by_code.get(project_code)
            manufacturing_error = manufacturing_error_by_code.get(manufacturing_code)
            internal_order_error = internal_order_error_by_code.get(internal_order_code)
            line_error = [purpose_error, department_error, analytic_error, project_error, manufacturing_error,
                          internal_order_error]
            line_error = list(filter(None, line_error))
            if line_error:
                line_error = ['Dòng %s, ' % row_idx + error for error in line_error]
                errors.append('\n'.join(line_error))
            else:
                value = {
                    'purpose_id': purpose_by_code.get(purpose_code),
                    'department_id': department_by_code.get(department_code),
                    'analytic_account_id': analytic_by_code.get(analytic_code),
                    'asset_id': project_by_code.get(project_code) or False,
                    'production_id': manufacturing_by_code.get(manufacturing_code) or False,
                    'occasion_code_id': internal_order_by_code.get(internal_order_code) or False,
                    'x_bhxh_level': float(row[7]) if row[7] else 0,
                    'x_bhxh_nld': float(row[8]) if row[8] else 0,
                    'x_bhyt_nld': float(row[9]) if row[9] else 0,
                    'x_bhtn_nld': float(row[10]) if row[10] else 0,
                    'x_tbh_nld': float(row[11]) if row[11] else 0,
                    'x_bhxh_bhbnn_tnld_ct': float(row[12]) if row[12] else 0,
                    'x_bhyt_ct': float(row[13]) if row[13] else 0,
                    'x_bhtn_ct': float(row[14]) if row[14] else 0,
                    'x_tbh_ct': float(row[15]) if row[15] else 0,
                    'x_cdp_ct': float(row[16]) if row[16] else 0,
                    'x_cdp_nld': float(row[17]) if row[17] else 0,
                    'x_tncn': float(row[18]) if row[18] else 0,
                    'note': row[19],
                }
                res.append(value)
        errors = '\n'.join(errors)
        return res, errors

    @api.model
    def read_salary_arrears_data(self, workbook, sheet_index=4):
        data = self.env['res.utility'].read_xls_book(workbook, sheet_index)
        data = [x for x in data]
        start_row = 1
        data = data[start_row:]
        res = []
        errors = []
        xls_purposes = []
        xls_employees_name_and_code = {}
        xls_departments_name_and_code = {}
        xls_analytic_accounts = []
        xls_projects = []
        xls_manufacturing = []
        xls_internal_orders = []

        for row_idx, row in enumerate(data, start=start_row):
            xls_purposes.append(row[0])
            xls_employees_name_and_code.update({row[1]: row[2]})
            xls_departments_name_and_code.update({row[3]: row[4]})
            xls_analytic_accounts.append(row[5])
            xls_projects.append(row[6])
            xls_manufacturing.append(row[7])
            xls_internal_orders.append(row[8])
        xls_data = dict(
            purpose=xls_purposes, employee=xls_employees_name_and_code, department=xls_departments_name_and_code,
            analytic=xls_analytic_accounts,
            project=xls_projects, manufacturing=xls_manufacturing, internal_order=xls_internal_orders
        )
        mapped_data = self.map_data(**xls_data)
        purpose_by_code, purpose_error_by_code = mapped_data.get('purpose')
        employee_by_code, employee_error_by_code = mapped_data.get('employee')
        department_by_code, department_error_by_code = mapped_data.get('department')
        analytic_by_code, analytic_error_by_code = mapped_data.get('analytic')
        project_by_code, project_error_by_code = mapped_data.get('project')
        manufacturing_by_code, manufacturing_error_by_code = mapped_data.get('manufacturing')
        internal_order_by_code, internal_order_error_by_code = mapped_data.get('internal_order')

        for row_idx, row in enumerate(data, start=start_row + 1):
            purpose_code = self.get_purpose_code(row[0])
            employee_code = row[1]
            department_code = row[3]
            analytic_code = row[5]
            project_code = row[6]
            manufacturing_code = row[7]
            internal_order_code = row[8]

            purpose_error = purpose_error_by_code.get(purpose_code)
            employee_error = employee_error_by_code.get(employee_code)
            department_error = department_error_by_code.get(department_code)
            analytic_error = analytic_error_by_code.get(analytic_code)
            project_error = project_error_by_code.get(project_code)
            manufacturing_error = manufacturing_error_by_code.get(manufacturing_code)
            internal_order_error = internal_order_error_by_code.get(internal_order_code)
            line_error = [purpose_error, employee_error, department_error, analytic_error, project_error,
                          manufacturing_error, internal_order_error]
            line_error = list(filter(None, line_error))
            if line_error:
                line_error = ['Dòng %d - %s' % (row_idx, error_message) for error_message in line_error]
                errors.append('\n'.join(line_error))
            else:
                value = {
                    'purpose_id': purpose_by_code.get(purpose_code),
                    'employee_id': employee_by_code.get(employee_code),
                    'department_id': department_by_code.get(department_code),
                    'analytic_account_id': analytic_by_code.get(analytic_code),
                    'asset_id': project_by_code.get(project_code) or False,
                    'production_id': manufacturing_by_code.get(manufacturing_code) or False,
                    'occasion_code_id': internal_order_by_code.get(internal_order_code) or False,
                    'x_kq': float(row[9]) if row[9] else 0,
                    'x_tkdp': float(row[10]) if row[10] else 0,
                    'x_pvp': float(row[11]) if row[11] else 0,
                    'x_tthh': float(row[12]) if row[12] else 0,
                    'x_thl': float(row[13]) if row[13] else 0,
                    'x_dpfm': float(row[14]) if row[14] else 0,
                    'x_pds': float(row[15]) if row[15] else 0,
                    'x_ttl': float(row[16]) if row[16] else 0,
                    'x_ttpc': float(row[17]) if row[17] else 0,
                    'x_tu': float(row[18]) if row[18] else 0,
                    'x_tk': float(row[19]) if row[19] else 0,
                    'x_bhxh_cn': float(row[20]) if row[20] else 0,
                    'x_bhyt_cn': float(row[21]) if row[21] else 0,
                    'x_bhxh_bhbnn_tnld_cn': float(row[22]) if row[22] else 0,
                    'x_ttbh': float(row[23]) if row[23] else 0,
                    'note': row[24],
                }
                res.append(value)
        errors = '\n'.join(errors)
        return res, errors

    @api.model
    def read_salary_backlog_data(self, workbook, sheet_index=5):
        data = self.env['res.utility'].read_xls_book(workbook, sheet_index)
        data = [x for x in data]
        start_row = 1
        data = data[start_row:]
        res = []
        errors = []
        xls_employees_name_and_code = {}
        xls_departments_name_and_code = {}
        for row_idx, row in enumerate(data):
            xls_employees_name_and_code.update({row[1]: row[2]})
            xls_departments_name_and_code.update({row[3]: row[4]})
        xls_data = dict(employee=xls_employees_name_and_code, department=xls_departments_name_and_code)
        mapped_data = self.map_data(**xls_data)
        employee_by_code, employee_error_by_code = mapped_data.get('employee')
        department_by_code, department_error_by_code = mapped_data.get('department')

        for row_idx, row in enumerate(data, start=start_row + 1):
            employee_code = row[1]
            department_code = row[3]
            period = row[6]
            month = int(period.split('.')[0])
            year = int(period.split('.')[1])

            employee_error = employee_error_by_code.get(employee_code)
            department_error = department_error_by_code.get(department_code)
            line_error = [employee_error, department_error]
            line_error = list(filter(None, line_error))
            if line_error:
                line_error = ['Dòng %d - %s' % (row_idx, error_message) for error_message in line_error]
                errors.append('\n'.join(line_error))
            else:
                value = {
                    'employee_id': employee_by_code.get(employee_code),
                    'department_id': department_by_code.get(department_code),
                    'amount': float(row[5]) if row[5] else 0,
                    'month': month,
                    'year': year
                }
                res.append(value)

        errors = '\n'.join(errors)
        return res, errors
