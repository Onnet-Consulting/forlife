# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BusinessObjectivePlan(models.Model):
    _name = 'business.objective.plan'
    _description = 'Business objective plan'
    _order = 'id desc'

    name = fields.Char('Name', required=True)
    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    brand_id = fields.Many2one("res.brand", string="Brand", required=True)
    bo_store_ids = fields.One2many('business.objective.store', 'bo_plan_id', 'Business objective store')
    bo_employee_ids = fields.One2many('business.objective.employee', 'bo_plan_id', 'Business objective employee')
    bo_store_temp_ids = fields.One2many('business.objective.store', 'bo_plan_temp_id', 'BOS temp')
    bo_employee_temp_ids = fields.One2many('business.objective.employee', 'bo_plan_temp_id', 'BOE temp')
    is_lock_brand = fields.Boolean(compute='_compute_lock_brand', store=True)

    @api.depends('bo_store_ids', 'bo_employee_ids')
    def _compute_lock_brand(self):
        for line in self:
            if line.bo_store_ids or line.bo_employee_ids:
                line.is_lock_brand = True
            else:
                line.is_lock_brand = False

    @api.constrains("from_date", "to_date", "brand_id")
    def validate_time(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))
            domain = ['&', '&', ('brand_id', '=', self.brand_id.id), ('id', '!=', self.id),
                      '|', '|', '&', ('from_date', '<=', self.from_date), ('to_date', '>=', self.from_date),
                      '&', ('from_date', '<=', self.to_date), ('to_date', '>=', self.to_date),
                      '&', ('from_date', '>', self.from_date), ('to_date', '<', self.to_date)]
            if self.search_count(domain) > 0:
                raise ValidationError(_("Time of BOL '%s' is overlapping.") % record.name)

    def btn_import_excel(self):
        self.ensure_one()
        action = self.env.ref('forlife_business_objective_plan.bo_import_excel_wizard_action').read()[0]
        action['context'] = dict(self._context, default_bo_plan_id=self.id)
        return action

    def btn_create_manual(self):
        view = self.env.ref('forlife_business_objective_plan.business_objective_plan_view_form_create_temp')
        context = dict(self._context, default_bo_plan_temp_id=self.id, default_bo_plan_id=self.id, brand_id=self.brand_id.id)
        return {
            'name': _('Create'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'business.objective.plan',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
            'res_id': self.id,
        }

    def btn_save(self):
        self.bo_store_temp_ids.write({
            'bo_plan_temp_id': False,
        })
        self.bo_employee_temp_ids.write({
            'bo_plan_temp_id': False,
        })

    def open_business_objective(self):
        self.ensure_one()
        action = self.env.ref(f'forlife_business_objective_plan.{self._context.get("action_xml_id")}').read()[0]
        action['domain'] = [('bo_plan_id', '=', self.id)]
        return action
