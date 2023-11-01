# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

BravoTableDetail = 'B30StatsDocDetail'
BravoTable = 'B30StatsDoc'


class ForLifeProduction(models.Model):
    _name = 'forlife.production'
    _inherit = ['forlife.production', 'bravo.model.insert.action']

    @api.model
    def bravo_get_filter_domain(self, **kwargs):
        return ['&', '&', ('state', '=', 'approved'), ('production_department', 'in', ('tu_san_xuat', 'tp')), ('active', '=', True)]

    def action_approved(self):
        res = super().action_approved()
        if self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            self.sync_to_b30_stats_doc()
            self.sync_to_b30_stats_doc_detail()
        return res

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        if (kwargs.get('bravo_table') or '') != BravoTableDetail:
            return super().bravo_get_default_insert_value(**kwargs)
        return {'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'"}

    @api.model
    def bravo_get_table(self, **kwargs):
        return kwargs.get('bravo_table')

    def bravo_get_insert_values(self, **kwargs):
        bravo_table = kwargs.get('bravo_table') or ''
        column_names = []
        values = []
        if bravo_table == BravoTableDetail:
            column_names = [
                'StatsDocId', 'ItemCode', 'ItemName', 'UnitCode', 'NormQuantityUnit', 'NormAmountUnit', 'NormQuantityUnit9',
                'NormQuantity', 'LossRate', 'Quantity9', 'Quantity', 'NormAmount', 'CustomerCode', 'DebitAccount',
                'CreditAccount', 'DeptCode', 'ExpenseCatgCode', 'JobCode', 'CustomFieldCode', 'DueDate', 'Remark', 'NormQuantity9',
            ]

            for record in self:
                for material in record.material_import_ids:
                    values.append({
                        'StatsDocId': record.code or None,
                        'ItemCode': material.product_id.barcode or None,
                        'ItemName': material.product_id.name or None,
                        'UnitCode': material.production_uom_id.code or None,
                        'NormQuantityUnit9': material.rated_level,
                        'NormQuantityUnit': material.rated_level * material.conversion_coefficient,
                        'NormAmountUnit': 1,
                        'NormQuantity9': material.rated_level * material.qty,
                        'NormQuantity': material.rated_level * material.qty * material.conversion_coefficient,
                        'LossRate': material.loss or 0,
                        'Quantity9': (material.rated_level * material.qty or 0) * (1 + (material.loss or 0) / 100),
                        'Quantity': (material.rated_level * material.qty or 0) * (1 + (material.loss or 0) / 100) * (material.conversion_coefficient or 0),
                        'NormAmount': 0,
                        'CustomerCode': record.machining_id.ref or None,
                        'DebitAccount': None,
                        'CreditAccount': None,
                        'DeptCode': None,
                        'ExpenseCagld': None,
                        'JobCode': None,
                        'CustomFieldCode': None,
                        'DueDate': None,
                        'Remark': None,
                    })
                for expense in record.expense_import_ids:
                    values.append({
                        'StatsDocId': record.code or None,
                        'ItemCode': expense.product_id.barcode or None,
                        'ItemName': expense.product_id.name or None,
                        'UnitCode': expense.product_id.uom_id.code or None,
                        'NormQuantityUnit9': 1,
                        'NormQuantityUnit': 1,
                        'NormAmountUnit': expense.cost_norms or 0,
                        'NormQuantity9': expense.quantity or 0,
                        'NormQuantity': expense.quantity or 0,
                        'LossRate': 0,
                        'Quantity9': 0,
                        'Quantity': 0,
                        'NormAmount': expense.total_cost_norms or 0,
                        'CustomerCode': record.machining_id.ref or None,
                        'DebitAccount': None,
                        'CreditAccount': None,
                        'DeptCode': None,
                        'ExpenseCagld': None,
                        'JobCode': None,
                        'CustomFieldCode': None,
                        'DueDate': None,
                        'Remark': None,
                    })

        if bravo_table == BravoTable:
            column_names = [
                'CompanyCode', 'DocNo', 'DocDate', 'Name', 'StartDate', 'EndDate', 'DeptCode', 'StatsDocType',
                'BrandsCode', 'EmployeeCode', 'ManagementDeptCode', 'UnitCode', 'CustomerCode', 'UnitLabor', 'ProductQuantity'
            ]
            x_type = {
                "tu_san_xuat": 1,
                "tp": 2,
            }
            employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
            for record in self:
                user_id = str(record.user_id.id or self._uid)
                employee = employees.get(user_id) or {}
                values.append({
                    'CompanyCode': record.company_id.code or None,
                    'DocNo': record.code or None,
                    'DocDate': record.create_date or None,
                    'Name': record.name or None,
                    'StartDate': record.produced_from_date or None,
                    'EndDate': record.to_date or None,
                    'DeptCode': record.implementation_id.code or None,
                    'StatsDocType': x_type.get(record.production_department) or None,
                    'BrandsCode': record.brand_id.code or None,
                    'EmployeeCode': employee.get('code') or None,
                    'ManagementDeptCode': record.management_id.code or None,
                    'UnitCode': (record.forlife_production_finished_product_ids
                                 and record.forlife_production_finished_product_ids[0].uom_id.code) or None,
                    'CustomerCode': record.machining_id.ref or None,
                    'UnitLabor': record.production_price or 0,
                    'ProductQuantity': (record.forlife_production_finished_product_ids
                                        and sum(record.forlife_production_finished_product_ids.mapped('produce_qty'))) or 0,
                })

        return column_names, values

    def sync_to_b30_stats_doc_detail(self):
        record = self.filtered_domain(self.bravo_get_filter_domain())
        if not record:
            return False
        queries = record.bravo_get_insert_sql(bravo_table=BravoTableDetail)
        if queries:
            if len(record) == 1:
                bravo_condition = f"StatsDocId = '{record.code}'"
            else:
                bravo_condition = ' or '.join([f"StatsDocId = '{r.code}'" for r in record])
            x_query = f"delete from {BravoTableDetail} where {bravo_condition};\n" + queries[0][0]
            x_query = [(x_query, queries[0][1])]
            self.env[self._name].with_delay(description=f"Bravo: Chứng từ lệnh sản xuất chi tiết", channel="root.Bravo").bravo_execute_query(x_query)
        return True

    def sync_to_b30_stats_doc(self):
        record = self.filtered_domain(self.bravo_get_filter_domain())
        if not record:
            return False
        queries = record.bravo_get_insert_sql(bravo_table=BravoTable)
        if queries:
            if len(record) == 1:
                bravo_condition = f"DocNo = '{record.code}'"
            else:
                bravo_condition = ' or '.join([f"DocNo = '{r.code}'" for r in record])
            x_query = f"delete from {BravoTable} where {bravo_condition};\n" + queries[0][0]
            x_query = [(x_query, queries[0][1])]
            self.env[self._name].with_delay(description=f"Bravo: Chứng từ lệnh sản xuất", channel="root.Bravo").bravo_execute_query(x_query)
        return True
