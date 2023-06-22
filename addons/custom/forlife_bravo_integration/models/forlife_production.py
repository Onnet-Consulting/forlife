# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from ..fields import BravoCharField, BravoDatetimeField, BravoDateField, BravoMany2oneField, BravoSelectionField, \
    BravoDecimalField


class ForLifeProduction(models.Model):
    _name = 'forlife.production'
    _inherit = ['forlife.production', 'bravo.model']
    _bravo_table = 'B30StatsDoc'

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

    br1 = BravoMany2oneField("res.company", odoo_name="company_id", bravo_name="CompanyCode",
                             field_detail="code")
    br2 = BravoCharField(odoo_name="code", bravo_name="DocNo", identity=True)
    br3 = BravoDatetimeField(odoo_name="create_date", bravo_name="DocDate")
    br4 = BravoCharField(odoo_name="name", bravo_name="Name")
    br5 = BravoDateField(odoo_name="produced_from_date", bravo_name="StartDate")
    br6 = BravoDateField(odoo_name="to_date", bravo_name="EndDate")
    br7 = BravoMany2oneField('account.analytic.account', odoo_name='implementation_id', bravo_name='DeptCode',
                             field_detail="code")
    br8 = BravoSelectionField(odoo_name='production_department', bravo_name='StatsDocType',
                              mapping_selection={
                                  "tu_san_xuat": 1,
                                  "tp": 2,
                                  "npl": 2
                              })
    br9 = BravoMany2oneField('res.brand', odoo_name="brand_id", bravo_name="BrandsCode", field_detail="code")
    br10 = BravoMany2oneField('hr.employee', odoo_name="user_id", bravo_name="EmployeeCode", field_detail="code")
    br11 = BravoMany2oneField('account.analytic.account', odoo_name='management_id', bravo_name='ManagementDeptCode',
                              field_detail="code")
    br12 = BravoMany2oneField('uom.uom', odoo_name="br_line_uom_id", bravo_name="UnitCode", field_detail="code")
    br13 = BravoDecimalField(odoo_name="br_line_total_qty", bravo_name="ProductQuantity")
