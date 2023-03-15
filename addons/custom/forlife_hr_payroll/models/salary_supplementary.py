# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

NUMBER_FIELDS = ["x_bhxh_level", "x_bhxh_nld", "x_bhyt_nld", "x_bhtn_nld", "x_tbh_nld", "x_bhxh_bhbnn_tnld_ct", "x_bhyt_ct", "x_bhtn_ct", "x_tbh_ct", "x_cdp_ct", "x_cdp_nld", "x_tncn"]


class SalarySupplementary(models.Model):
    _name = 'salary.supplementary'
    _inherit = 'salary.general.info'
    _description = 'Salary Supplementary'  # BH+phí CĐ+thuế TNCN cần chi trả

    x_bhxh_level = fields.Float(string="Mức BHXH")
    x_bhxh_nld = fields.Float(string="BHXH NLĐ chi trả")
    x_bhyt_nld = fields.Float(string="BHYT NLĐ chi trả")
    x_bhtn_nld = fields.Float(string="BHTN NLĐ chi trả")
    x_tbh_nld = fields.Float(string="TỔNG CHI PHÍ BH NLĐ chi trả")
    x_bhxh_bhbnn_tnld_ct = fields.Float(string="BHXH+BHBNN-TNLĐ Công ty chi trả")
    x_bhyt_ct = fields.Float(string="BHYT Công ty chi trả")
    x_bhtn_ct = fields.Float(string="BHTN Công ty chi trả")
    x_tbh_ct = fields.Float(string="TỔNG CHI PHÍ BH Công ty chi trả")
    x_cdp_ct = fields.Float(string="Công đoàn phí công ty nộp")
    x_cdp_nld = fields.Float(string="Công đoàn phí NLĐ nộp")
    x_tncn = fields.Float(string="Thuế TNCN NLĐ nộp")
    note = fields.Text(string='Note')

    @api.constrains(*NUMBER_FIELDS)
    def _check_numbers(self):
        fields_desc = self.fields_get(NUMBER_FIELDS, ['string'])
        for rec in self:
            for num_field in NUMBER_FIELDS:
                if rec[num_field] < 0:
                    raise ValidationError(_("Field '%s' value in the table '%s' must be >= 0") % (fields_desc[num_field]['string'], self._description))
