# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ForlifeQuestion(models.Model):
    _name = 'forlife.question'
    _description = 'Question'
    _rec_name = 'name'
    _order = 'finish_date desc'

    name = fields.Char('Name', required=True)
    header = fields.Text('Header', required=True)
    question1 = fields.Text("Question 1", required=True)
    sub_quest1 = fields.Char('Sub Question 1', required=True)
    sub_quest2 = fields.Char('Sub Question 2')
    question2 = fields.Text("Question 2")
    success1 = fields.Text("Success 1", required=True)
    success2 = fields.Text("Success 2")
    success3 = fields.Text("Success 3")
    brand_id = fields.Many2one('res.brand', string='Brand', required=True)
    start_date = fields.Datetime('Start Date', required=True)
    finish_date = fields.Datetime('Finish Date', required=True)
    create_uid = fields.Many2one("res.users", string="Create By", default=lambda s: s.env.user)
    create_date = fields.Datetime("Create On", default=fields.Datetime.now())
    banner = fields.Char('Banner')
    icon = fields.Char('Icon')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('check_dates', 'CHECK (start_date <= finish_date)', 'Finish date may not be before the starting date.'),
    ]

    @api.constrains("start_date", "finish_date")
    def validate_time(self):
        for record in self:
            res = self.search(['&', ('brand_id', '=', record.brand_id.id), '&', ('id', '!=', record.id), '|', '&', ('start_date', '<=', record.start_date),
                               ('finish_date', '>=', record.start_date), '&', ('start_date', '<=', record.finish_date), ('finish_date', '>=', record.finish_date)])
            if res:
                raise ValidationError(_("Time is overlapping."))
