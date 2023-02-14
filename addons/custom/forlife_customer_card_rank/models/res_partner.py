# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_name(self):
        try:
            return self.name + ' tgjgktygkejrh'
        except:
            return super(ResPartner, self)._get_name()
