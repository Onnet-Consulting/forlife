# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeTransfer(models.Model):
    _name = 'employee.transfer'
    _description = 'Employee transfer'

    bo_plan_id = fields.Many2one('business.objective.plan', 'Business objective plan', ondelete='restrict')
    store_source_id = fields.Many2one('store', 'Store Source', ondelete='restrict', required=True)
    store_dest_id = fields.Many2one('store', 'Store Dest', ondelete='restrict', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete='restrict', required=True)
    job_id = fields.Many2one('hr.job', 'Job Position', ondelete='restrict')
    target_reduce = fields.Monetary('Target reduce', default=0)
    target_increase = fields.Monetary('Target increase', default=0)
    from_date = fields.Date(string='From date', required=True, default=fields.Date.context_today)
    to_date = fields.Date(string='To date', required=True)
    state = fields.Selection([('waiting_reduce', _('Waiting reduce')),
                              ('confirmed_reduce', _('Confirmed reduce')),
                              ('waiting_increase', _('Waiting increase')),
                              ('approved', _('Approved')),
                              ('cancelled', _('Cancelled'))], 'State', required=True, default='waiting_reduce')
    bo_employee_id = fields.Many2one('business.objective.employee', 'BOE source', ondelete='restrict')
    bo_employee_dest_id = fields.Many2one('business.objective.employee', 'BOE destination', ondelete='restrict')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    @api.constrains('store_source_id', 'store_dest_id')
    def check_store(self):
        for record in self:
            if record.store_source_id and record.store_dest_id and record.store_source_id == record.store_dest_id:
                raise ValidationError(_('Store source must be different from store destination'))

    @api.onchange('employee_id')
    def onchange_employee(self):
        self.job_id = self.employee_id.job_id

    def btn_confirm_reduce(self):
        self.ensure_one()
        self.write({'state': 'confirmed_reduce'})
        self.bo_employee_id.write({'revenue_target': self.bo_employee_id.revenue_target - self.target_reduce})

    def btn_receipt_transfer(self):
        self.ensure_one()
        self.write({'state': 'waiting_increase'})

    def btn_approve_transfer(self):
        self.ensure_one()
        BOE = self.env['business.objective.employee']
        bo_employee = BOE.search([('bo_plan_id', '=', self.bo_plan_id.id),
                                  ('store_id', '=', self.store_dest_id.id),
                                  ('employee_id', '=', self.employee_id.id),
                                  ('job_id', '=', self.job_id.id)], limit=1)
        if bo_employee:
            bo_employee.write({'revenue_target': bo_employee.revenue_target + self.target_increase})
        else:
            bo_employee = BOE.create({
                'bo_plan_id': self.bo_plan_id.id,
                'store_id': self.store_dest_id.id,
                'employee_id': self.employee_id.id,
                'job_id': self.job_id.id,
                'currency_id': self.currency_id.id,
                'sale_province_id': self.store_dest_id.warehouse_id.sale_province_id.id,
                'revenue_target': self.target_increase,
            })
        self.write({
            'state': 'approved',
            'bo_employee_dest_id': bo_employee.id,
        })

    def btn_cancel(self):
        self.ensure_one()
        self.bo_employee_id.write({'revenue_target': self.bo_employee_id.revenue_target + self.target_reduce})
        self.write({'state': 'cancelled'})

    def btn_cancel_approve(self):
        self.ensure_one()
        self.bo_employee_dest_id.write({'revenue_target': self.bo_employee_dest_id.revenue_target - self.target_increase})
        self.write({'state': 'confirmed_reduce'})
