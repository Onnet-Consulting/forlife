# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
import json
import logging
from ...bkav_connector.models.bkav_connector import connect_bkav

_logger = logging.getLogger(__name__)


class SyntheticAccountMovePos(models.Model):
    _name = 'synthetic.account.move.pos'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'code'

    code = fields.Char('Code')
    store_id = fields.Many2one('store')
    partner_id = fields.Many2one('res.partner')
    invoice_date = fields.Date('Date')
    state = fields.Selection([('draft', 'Nháp'),
                              ('posted', 'Đã vào sổ')], string="State", default='draft')
    line_ids = fields.One2many('synthetic.account.move.pos.line', 'synthetic_id')
    company_id = fields.Many2one('res.company')
    number_bill = fields.Char('Số hóa đơn')
    einvoice_status = fields.Selection([('draft', 'Nháp'), ('sign', 'Đã phát hành')], string=' Trạng thái HDDT', readonly=1)
    einvoice_date = fields.Date(string="Ngày phát hành")
    account_einvoice_serial = fields.Char('Mẫu số - Ký hiệu hóa đơn')
    invoice_guid = fields.Char('GUID HDDT')
    invoice_form = fields.Char('Mẫu số HDDT')
    partner_invoice_id = fields.Integer(string='Số hóa đơn')
    eivoice_file = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)

    def action_download_view_e_invoice(self):
        if not self.eivoice_file:
            configs = self.env['summary.account.move.pos'].get_bkav_config()
            data = {
                "CmdType": int(configs.get('cmd_downloadPDF')),
                "CommandObject": self.partner_invoice_id,
            }
            _logger.info(f'BKAV - data download invoice to BKAV: {data}')
            response_action = connect_bkav(data, configs)
            if response_action.get('Status') == '1':
                self.message_post(body=(response_action.get('Object')))
            else:
                attachment_id = self.env['ir.attachment'].sudo().create({
                    'name': f"{self.number_bill}.pdf",
                    'datas': json.loads(response_action.get('Object')).get('PDF', ''),
                })
                self.eivoice_file = attachment_id
                return {
                    'type': 'ir.actions.act_url',
                    'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                           % (self.eivoice_file.id, self.eivoice_file.name),
                    'target': 'self',
                }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                       % (self.eivoice_file.id, self.eivoice_file.name),
                'target': 'self',
            }

class SyntheticAccountMovePosLine(models.Model):
    _name = 'synthetic.account.move.pos.line'

    synthetic_id = fields.Many2one('synthetic.account.move.pos')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    barcode = fields.Char(related='product_id.barcode')
    description = fields.Char('Mô tả')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    quantity = fields.Float('Số lượng')
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Đơn vị")
    price_unit = fields.Float('Đơn giá')
    x_free_good = fields.Boolean('Hàng tặng')
    discount = fields.Float('% chiết khấu')
    discount_amount = fields.Monetary('Số tiền chiết khấu')
    tax_ids = fields.Many2many('account.tax', string='Thuế', related="product_id.taxes_id")
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="compute_tax_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="compute_price_subtotal")
    amount_total = fields.Monetary('Thành tiền', compute="compute_amount_total")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')
    summary_line_id = fields.Many2one('summary.account.move.pos.line')
    return_line_id = fields.Many2one('summary.account.move.pos.return.line')

    @api.depends('price_unit', 'quantity', 'discount_amount')
    def compute_price_subtotal(self):
        for r in self:
            r.price_subtotal = r.price_unit * r.quantity - r.discount_amount

    @api.depends('price_subtotal', 'tax_amount')
    def compute_amount_total(self):
        for r in self:
            r.amount_total = r.price_subtotal + r.tax_amount

    @api.depends('tax_ids', 'price_subtotal')
    def compute_tax_amount(self):
        for r in self:
            if r.tax_ids:
                tax_amount = 0
                for tax in r.tax_ids:
                    tax_amount += (r.price_subtotal * tax.amount) / 100
                r.tax_amount = tax_amount
            else:
                r.tax_amount = 0