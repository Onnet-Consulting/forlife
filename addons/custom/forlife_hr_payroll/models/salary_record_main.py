# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SalaryRecordMain(models.Model):
    _name = 'salary.record.main'
    _description = 'Salary Record Main'  # LƯƠNG

    salary_record_id = fields.Many2one('salary.record', string='Reference', ondelete="cascade", required=True, copy=False)
    company_id = fields.Many2one('res.company', related='salary_record_id.company_id', string='Company', store=True, readonly=True)
    purpose_id = fields.Many2one('salary.record.purpose', string='Purpose', required=True, ondelete='restrict')
    department_id = fields.Many2one('hr.department', string='Department', required=True, ondelete="restrict")
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Center', required=True, ondelete="restrict")

    asset_id = fields.Many2one('assets.assets', string='Project Code', ondelete="restrict")
    production_id = fields.Many2one('forlife.production', string='Manufacture Order Code', ondelete="restrict")
    occasion_code_id = fields.Many2one('occasion.code', string='Internal Order Code', ondelete="restrict")

    # FIXME: delete project_code, manufacture_order_code, internal_order_code fields below
    project_code = fields.Char(string='Project Code')
    manufacture_order_code = fields.Char(string='Manufacture Order Code')
    internal_order_code = fields.Char(string='Internal Order Code')
    # =========================================
    x_ttn = fields.Float(string="Tổng thu nhập", required=True, compute="_compute_values")
    x_kq = fields.Float(string="Ký quỹ", compute="_compute_values")
    x_tkdp = fields.Float(string="TKDP", compute="_compute_values")
    x_pvp = fields.Float(string="Phạt vi phạm", compute="_compute_values")
    x_tthh = fields.Float(string="Trừ TTHH", compute="_compute_values")
    x_thl = fields.Float(string="Trừ hàng lỗi", compute="_compute_values")
    x_dpfm = fields.Float(string="Trừ chi phí đồng phục FM", compute="_compute_values")
    x_pds = fields.Float(string="Phạt doanh số", compute="_compute_values")
    x_ttl = fields.Float(string="Truy thu lương", compute="_compute_values")
    x_ttpc = fields.Float(string="Truy thu phụ cấp", compute="_compute_values")
    x_tu = fields.Float(string="Tạm ứng", compute="_compute_values")
    x_ttbh = fields.Float(string="Truy thu BH vào lương", compute="_compute_values")
    x_tk = fields.Float(string="Trừ khác", compute="_compute_values")
    x_bhxh_level = fields.Float(string="Mức BHXH", compute="_compute_values")
    x_bhxh_bhbnn_tnld_ct = fields.Float(string="BHXH+BHBNN-TNLĐ Công ty chi trả", compute="_compute_values")
    x_bhyt_ct = fields.Float(string="BHYT Công ty chi trả", compute="_compute_values")
    x_bhtn_ct = fields.Float(string="BHTN Công ty chi trả", compute="_compute_values")
    x_tbh_ct = fields.Float(string="TỔNG CHI PHÍ BH Công ty chi trả", compute="_compute_values")
    x_bhxh_nld = fields.Float(string="BHXH NLĐ chi trả", compute="_compute_values")
    x_bhyt_nld = fields.Float(string="BHYT NLĐ chi trả", compute="_compute_values")
    x_bhtn_nld = fields.Float(string="BHTN NLĐ chi trả", compute="_compute_values")
    x_tbh_nld = fields.Float(string="TỔNG CHI PHÍ BH NLĐ chi trả", compute="_compute_values")
    x_cdp_ct = fields.Float(string="Công đoàn phí công ty nộp", compute="_compute_values")
    x_cdp_nld = fields.Float(string="Công đoàn phí NLĐ nộp", compute="_compute_values")
    x_tncn = fields.Float(string="Thuế TNCN NLĐ nộp", compute="_compute_values")
    x_tt = fields.Float(string="Tổng trừ", compute="_compute_values")
    x_tl = fields.Float(string="Thực lĩnh", compute="_compute_values")
    x_slns = fields.Integer(string="Số lượng nhân sự")
    total_income_ids = fields.Many2many('salary.total.income')
    supplementary_ids = fields.Many2many('salary.supplementary')
    arrears_ids = fields.Many2many('salary.arrears')

    @api.constrains('x_slns')
    def _check_x_slns(self):
        for rec in self:
            if rec.x_slns < 0:
                raise ValidationError(_("'Số lượng nhân sự' in Salary main table must >= 0!"))

    @api.depends('total_income_ids.x_ttn', 'supplementary_ids', 'arrears_ids')
    def _compute_values(self):
        for record in self:
            supplementary = record.supplementary_ids
            x_bhxh_level = sum(supplementary.mapped('x_bhxh_level'))
            x_bhxh_bhbnn_tnld_ct = sum(supplementary.mapped('x_bhxh_bhbnn_tnld_ct'))
            x_bhyt_ct = sum(supplementary.mapped('x_bhyt_ct'))
            x_bhtn_ct = sum(supplementary.mapped('x_bhtn_ct'))
            x_tbh_ct = sum(supplementary.mapped('x_tbh_ct'))
            x_bhxh_nld = sum(supplementary.mapped('x_bhxh_nld'))
            x_bhyt_nld = sum(supplementary.mapped('x_bhyt_nld'))
            x_bhtn_nld = sum(supplementary.mapped('x_bhtn_nld'))
            x_tbh_nld = sum(supplementary.mapped('x_tbh_nld'))
            x_cdp_ct = sum(supplementary.mapped('x_cdp_ct'))
            x_cdp_nld = sum(supplementary.mapped('x_cdp_nld'))
            x_tncn = sum(supplementary.mapped('x_tncn'))

            arrears = record.arrears_ids
            x_kq = sum(arrears.mapped('x_kq'))
            x_tkdp = sum(arrears.mapped('x_tkdp'))
            x_pvp = sum(arrears.mapped('x_pvp'))
            x_tthh = sum(arrears.mapped('x_tthh'))
            x_thl = sum(arrears.mapped('x_thl'))
            x_dpfm = sum(arrears.mapped('x_dpfm'))
            x_pds = sum(arrears.mapped('x_pds'))
            x_ttl = sum(arrears.mapped('x_ttl'))
            x_ttpc = sum(arrears.mapped('x_ttpc'))
            x_tu = sum(arrears.mapped('x_tu'))
            x_ttbh = sum(arrears.mapped('x_ttbh'))
            x_tk = sum(arrears.mapped('x_tk'))

            record.x_bhxh_level = x_bhxh_level
            record.x_bhxh_bhbnn_tnld_ct = x_bhxh_bhbnn_tnld_ct
            record.x_bhyt_ct = x_bhyt_ct
            record.x_bhtn_ct = x_bhtn_ct
            record.x_tbh_ct = x_tbh_ct
            record.x_bhxh_nld = x_bhxh_nld
            record.x_bhyt_nld = x_bhyt_nld
            record.x_bhtn_nld = x_bhtn_nld
            record.x_tbh_nld = x_tbh_nld
            record.x_cdp_ct = x_cdp_ct
            record.x_cdp_nld = x_cdp_nld
            record.x_tncn = x_tncn

            record.x_kq = x_kq
            record.x_tkdp = x_tkdp
            record.x_pvp = x_pvp
            record.x_tthh = x_tthh
            record.x_thl = x_thl
            record.x_dpfm = x_dpfm
            record.x_pds = x_pds
            record.x_ttl = x_ttl
            record.x_ttpc = x_ttpc
            record.x_tu = x_tu
            record.x_ttbh = x_ttbh
            record.x_tk = x_tk

            x_ttn = sum(record.total_income_ids.mapped('x_ttn'))
            x_tt = sum([x_kq, x_tkdp, x_pvp, x_tthh, x_thl, x_dpfm, x_pds, x_ttl, x_ttpc, x_tu, x_ttbh, x_tk, x_tbh_nld, x_cdp_nld, x_tncn])
            x_tl = x_ttn - x_tt
            record.x_ttn = x_ttn
            record.x_tt = x_tt
            record.x_tl = x_tl

    _sql_constraints = [
        (
            'unique_combination_value',
            'UNIQUE(salary_record_id,purpose_id,department_id,analytic_account_id,asset_id)',
            'The combination of Reference, Purpose, Department, Cost Center and Project Code must be unique !'
        )
    ]
