# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SummaryPopupWizard(models.TransientModel):
    _name = 'summary.popup.wizard'
    _description = 'Summary popup wizard'

    x_ttn = fields.Float(string="Tổng thu nhập")
    x_kq = fields.Float(string="Ký quỹ")
    x_tkdp = fields.Float(string="TKDP")
    x_pvp = fields.Float(string="Phạt vi phạm")
    x_tthh = fields.Float(string="Trừ TTHH")
    x_thl = fields.Float(string="Trừ hàng lỗi")
    x_dpfm = fields.Float(string="Trừ chi phí đồng phục FM")
    x_pds = fields.Float(string="Phạt doanh số")
    x_ttl = fields.Float(string="Truy thu lương")
    x_ttpc = fields.Float(string="Truy thu phụ cấp")
    x_tu = fields.Float(string="Tạm ứng")
    x_ttbh = fields.Float(string="Truy thu BH vào lương")
    x_tk = fields.Float(string="Trừ khác")
    x_bhxh_level = fields.Float(string="Mức BHXH")
    x_bhxh_bhbnn_tnld_ct = fields.Float(string="BHXH+BHBNN-TNLĐ Công ty chi trả")
    x_bhyt_ct = fields.Float(string="BHYT Công ty chi trả")
    x_bhtn_ct = fields.Float(string="BHTN Công ty chi trả")
    x_tbh_ct = fields.Float(string="TỔNG CHI PHÍ BH Công ty chi trả")
    x_bhxh_nld = fields.Float(string="BHXH NLĐ chi trả")
    x_bhyt_nld = fields.Float(string="BHYT NLĐ chi trả")
    x_bhtn_nld = fields.Float(string="BHTN NLĐ chi trả")
    x_tbh_nld = fields.Float(string="TỔNG CHI PHÍ BH NLĐ chi trả")
    x_cdp_ct = fields.Float(string="Công đoàn phí công ty nộp")
    x_cdp_nld = fields.Float(string="Công đoàn phí NLĐ nộp")
    x_tncn = fields.Float(string="Thuế TNCN NLĐ nộp")
    x_tt = fields.Float(string="Tổng trừ")
    x_tl = fields.Float(string="Thực lĩnh")
    x_slns = fields.Integer(string="Số lượng nhân sự")
    x_bhxh_cn = fields.Float(string="Công nợ BHXH NLĐ chi trả")
    x_bhyt_cn = fields.Float(string="Công nợ BHYT NLĐ chi trả")
    x_bhxh_bhbnn_tnld_cn = fields.Float(string="Công nợ BHTN NLĐ chi trả")
    amount = fields.Float(string='Tổng tiền')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
