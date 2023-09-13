# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField, \
    BravoDecimalField

BravoTableDetail = 'B30StatsDocDetail'


class ForLifeProduction(models.Model):
    _name = 'forlife.production'
    _inherit = ['forlife.production', 'bravo.model']
    _bravo_table = 'B30StatsDoc'
    _bravo_field_sync = [
        'company_id', 'code', 'create_date', 'name', 'produced_from_date', 'to_date', 'implementation_id', 'production_price',
        'production_department', 'brand_id', 'user_id', 'management_id', 'br_line_uom_id', 'br_line_total_qty', 'machining_id'
    ]

    @api.model
    def bravo_get_filter_domain(self, **kwargs):
        return ['&', '&', ('state', '=', 'approved'), ('production_department', 'in', ('tu_san_xuat', 'tp')), ('active', '=', True)]

    @api.depends('forlife_production_finished_product_ids.produce_qty')
    def _compute_line_value(self):
        for rec in self:
            if not rec.forlife_production_finished_product_ids:
                rec.br_line_total_qty = 0
                rec.br_line_uom_id = False
            else:
                rec.br_line_total_qty = sum(rec.forlife_production_finished_product_ids.mapped('produce_qty'))
                rec.br_line_uom_id = rec.forlife_production_finished_product_ids[0].uom_id.id

    br_line_total_qty = fields.Float(compute="_compute_line_value")
    br_line_uom_id = fields.Many2one('uom.uom', compute="_compute_line_value")

    br1 = BravoMany2oneField("res.company", odoo_name="company_id", bravo_name="CompanyCode", field_detail="code")
    br2 = BravoCharField(odoo_name="code", bravo_name="DocNo", identity=True)
    br3 = BravoDatetimeField(odoo_name="create_date", bravo_name="DocDate")
    br4 = BravoCharField(odoo_name="name", bravo_name="Name")
    br5 = BravoDateField(odoo_name="produced_from_date", bravo_name="StartDate")
    br6 = BravoDateField(odoo_name="to_date", bravo_name="EndDate")
    br7 = BravoMany2oneField('account.analytic.account', odoo_name='implementation_id', bravo_name='DeptCode', field_detail="code")
    br8 = BravoSelectionField(odoo_name='production_department', bravo_name='StatsDocType',
                              mapping_selection={
                                  "tu_san_xuat": 1,
                                  "tp": 2,
                              })
    br9 = BravoMany2oneField('res.brand', odoo_name="brand_id", bravo_name="BrandsCode", field_detail="code")
    br10 = BravoMany2oneField('res.users', odoo_name="user_id", bravo_name="EmployeeCode", field_detail="employee_id.code")
    br11 = BravoMany2oneField('account.analytic.account', odoo_name='management_id', bravo_name='ManagementDeptCode', field_detail="code")
    br12 = BravoMany2oneField('uom.uom', odoo_name="br_line_uom_id", bravo_name="UnitCode", field_detail="code")
    br13 = BravoDecimalField(odoo_name="br_line_total_qty", bravo_name="ProductQuantity")
    br14 = BravoDecimalField(odoo_name="production_price", bravo_name="UnitLabor")
    br15 = BravoMany2oneField('res.partner', odoo_name='machining_id', bravo_name='CustomerCode', field_detail="ref")

    def action_approved(self):
        res = super().action_approved()
        if self.env['ir.config_parameter'].sudo().get_param("integration.bravo.up"):
            self.sync_to_b30_stats_doc_detail()
        return res

    @api.model
    def bravo_get_default_insert_value(self, **kwargs):
        if (kwargs.get('bravo_table') or '') != BravoTableDetail:
            return super().bravo_get_default_insert_value(**kwargs)
        return {'PushDate': "SYSDATETIMEOFFSET() AT TIME ZONE 'SE Asia Standard Time'"}

    @api.model
    def bravo_get_table(self, **kwargs):
        return kwargs.get('bravo_table') or super().bravo_get_table(**kwargs)

    def bravo_get_insert_values(self, **kwargs):
        if (kwargs.get('bravo_table') or '') != BravoTableDetail:
            return super().bravo_get_insert_values(**kwargs)
        column_names = [
            'StatsDocId', 'ItemCode', 'ItemName', 'UnitCode', 'NormQuantityUnit', 'NormAmountUnit',
            'NormQuantity', 'LossRate', 'Quantity9', 'Quantity', 'NormAmount', 'CustomerCode', 'DebitAccount',
            'CreditAccount', 'DeptCode', 'ExpenseCagId', 'JobCode', 'CustomFieldCode', 'DueDate', 'Remark'
        ]
        values = []
        for record in self:
            for material in record.material_import_ids:
                values.append({
                    'StatsDocId': record.code or None,
                    'ItemCode': material.product_id.barcode or None,
                    'ItemName': material.product_id.name or None,
                    'UnitCode': material.production_uom_id.code or None,
                    'NormQuantityUnit': material.rated_level or 0,
                    'NormAmountUnit': 0,
                    'NormQuantity': material.total or 0,
                    'LossRate': material.loss or 0,
                    'Quantity9': (material.total or 0) * (1 + (material.loss or 0) / 100),
                    'Quantity': (material.total or 0) * (1 + (material.loss or 0) / 100) * (material.conversion_coefficient or 0),
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
                    'NormQuantityUnit': 1,
                    'NormAmountUnit': expense.cost_norms or 0,
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
            self.env[self._name].with_delay(description=f"Bravo: Chứng từ lệnh sản xuất", channel="root.Bravo").bravo_execute_query(x_query)
        return True
