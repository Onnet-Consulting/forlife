from odoo import api, fields, models, _


class ForlifeReasonType(models.Model):
    _name = 'forlife.reason.type'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
