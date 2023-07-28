# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
import json
import logging
from ...bkav_connector.models.bkav_connector import connect_bkav
_logger = logging.getLogger(__name__)


class SummaryAdjustedInvoicePos(models.Model):
    _name = 'summary.adjusted.invoice.pos'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'code'

    code = fields.Char('Code')
    store_id = fields.Many2one('store')
    partner_id = fields.Many2one('res.partner')
    source_invoice = fields.Many2one('synthetic.account.move.pos',
                                     string='Hóa đơn gốc')
    source_einvoice = fields.Char(string='Hóa đơn điện tử gốc')

    invoice_date = fields.Date('Date')
    state = fields.Selection([('draft', 'Nháp'),
                              ('posted', 'Đã vào sổ')], string="State", default='draft')
    line_ids = fields.One2many('summary.adjusted.invoice.pos.line', 'adjusted_invoice_id')
    company_id = fields.Many2one('res.company')

    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    invoice_guid = fields.Char('GUID HDDT')
    invoice_no = fields.Char('Số hóa đơn')
    invoice_form = fields.Char('Mẫu số HDDT')
    invoice_serial = fields.Char('Mẫu số - Ký hiệu hóa đơn')
    invoice_e_date = fields.Date(string="Ngày phát hành")
    einvoice_status = fields.Selection([('draft', 'Nháp'), ('sign', 'Đã phát hành')], string=' Trạng thái HDDT', readonly=1)
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


    def get_vat(self, line):
        vat = 0
        if line.tax_ids:
            vat = line.tax_ids[0].amount

        if vat == 0:
            tax_rate_id = 1
        elif vat == 5:
            tax_rate_id = 2
        elif vat == 8:
            tax_rate_id = 9
        elif vat == 10:
            tax_rate_id = 3
        else:
            tax_rate_id = 4
        return vat, tax_rate_id

    def get_item_type_bkav(self, line):
        item_type = 0
        if line.x_free_good:
            item_type = 15
        return item_type

    def get_bkav_data_pos(self):
        bkav_invoices = []
        for ln in self:
            invoice_date = fields.Datetime.context_timestamp(ln, datetime.combine(datetime.now(), datetime.now().time()))
            ln_invoice = {
                "InvoiceTypeID": 1,
                "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                "BuyerName": str(ln.partner_id.name).strip() if ln.partner_id.name else '',
                "BuyerTaxCode": str(ln.partner_id.vat).strip() if ln.partner_id.vat else '',
                "BuyerUnitName": str(ln.partner_id.name).strip() if ln.partner_id.name else '',
                "BuyerAddress": str(ln.partner_id.country_id.name).strip() if ln.partner_id.country_id.name else '',
                "BuyerBankAccount": "",
                "PayMethodID": 7,
                "ReceiveTypeID": 3,
                "ReceiverEmail": str(ln.company_id.email).strip() if ln.company_id.email else '', 
                "ReceiverMobile": str(ln.company_id.mobile).strip() if ln.company_id.mobile else '', 
                "ReceiverAddress": str(ln.company_id.street).strip() if ln.company_id.street else '', 
                "ReceiverName": str(ln.company_id.name).strip() if ln.company_id.name else '', 
                "Note": "Hóa đơn mới tạo",
                "BillCode": "",
                "CurrencyID": str(ln.company_id.currency_id.name).strip() if ln.company_id.currency_id.name else '',
                "ExchangeRate": 1.0,
                "InvoiceForm": "",
                "InvoiceSerial": "",
                "InvoiceNo": 0,
                "ListInvoiceDetailsWS": [],
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": ln.code,
            }
            for line in ln.line_ids:
                line_invoice = {
                    "ItemName": line.product_id.name if line.product_id.name else '',
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.quantity or 0.0,
                    "Price": line.price_unit,
                    "Amount": line.price_subtotal,
                    "TaxAmount": (line.tax_amount or 0.0),
                    "DiscountRate": 0.0,
                    "DiscountAmount":0.0,
                    "IsDiscount": 0,
                    "ItemTypeID": self.get_item_type_bkav(line),
                }
                vat, tax_rate_id = self.get_vat(line)
                line_invoice.update({
                    "TaxRateID": tax_rate_id,
                    "TaxRate": vat
                })
                ln_invoice["ListInvoiceDetailsWS"].append(line_invoice)
            bkav_invoices.append({
                "Invoice": ln_invoice
            })
        return bkav_invoices

    def create_an_invoice(self):
        for line in self:
            try:
                bkav_invoice_data = line.get_bkav_data_pos()
                bkav_action.create_invoice_bkav(line, bkav_invoice_data, is_publish=True)
            except Exception as e:
                line.message_post(body=str(e))
            
class SummaryAdjustedInvoicePosLine(models.Model):
    _name = 'summary.adjusted.invoice.pos.line'

    adjusted_invoice_id = fields.Many2one('summary.adjusted.invoice.pos')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
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

    @api.depends('price_subtotal', 'tax_amount')
    def compute_amount_total(self):
        for r in self:
            r.amount_total = r.price_subtotal + r.tax_amount

    @api.depends('price_unit', 'quantity', 'discount_amount')
    def compute_price_subtotal(self):
        for r in self:
            r.price_subtotal = r.price_unit * r.quantity - r.discount_amount

    @api.depends('tax_ids', 'price_subtotal')
    def compute_tax_amount(self):
        for r in self:
            if r.tax_ids:
                r.tax_amount = sum(r.tax_ids.mapped('amount')) * r.price_subtotal
            else:
                r.tax_amount = 0
