# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class IrCron(models.Model):
    _inherit = 'ir.cron'

    mail_template_id = fields.Many2one('mail.template', string=_("Mail Template"), invisible=lambda self: self == self.env.ref('forlife_point_of_sale.noti_pos_not_closed'), default=lambda self: self.env.ref('forlife_point_of_sale.mail_template_warning_opened_pos'))

