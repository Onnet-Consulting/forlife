# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
import json
from .bkav_connector import connect_bkav

_logger = logging.getLogger(__name__)

disable_create_function = False
class GeneralInvoiceNotExistsBkav(models.Model):
    _name = 'invoice.not.exists.bkav'
    _description = 'General Invoice Not Exists Bkav'
    _rec_name = 'id'
    _order = 'id desc'

    move_date = fields.Date('Ngày tổng hợp', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Đối tác')

    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav = fields.Boolean(default=False, copy=False, string="Đã ký HĐ trên BKAV")
    is_check_cancel = fields.Boolean(default=False, copy=False, string="Đã hủy")

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status_get_values', store=1,
                                  copy=False)
    invoice_guid = fields.Char('GUID HDDT', copy=False)
    invoice_no = fields.Char('Số HDDT', copy=False)
    invoice_form = fields.Char('Mẫu số HDDT', copy=False)
    invoice_serial = fields.Char('Ký hiệu HDDT', copy=False)
    invoice_e_date = fields.Datetime('Ngày HDDT', copy=False)

    data_compare_status = fields.Selection([('1', 'Mới tạo'),
                                            ('2', 'Đã phát hành'),
                                            ('3', 'Đã hủy'),
                                            ('4', 'Đã xóa'),
                                            ('5', 'Chờ thay thế'),
                                            ('6', 'Thay thế'),
                                            ('7', 'Chờ điều chỉnh'),
                                            ('8', 'Điều chỉnh'),
                                            ('9', 'Bị thay thế'),
                                            ('10', 'Bị điều chỉnh'),
                                            ('11', 'Trống (Đã cấp số, Chờ ký)'),
                                            ('12', 'Không sử dụng'),
                                            ('13', 'Chờ huỷ'),
                                            ('14', 'Chờ điều chỉnh chiết khấu'),
                                            ('15', 'Điều chỉnh chiết khấu')], copy=False)

    eivoice_file = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)
    issue_invoice_type = fields.Selection([
        ('vat', 'GTGT'),
        ('adjust', 'Điều chỉnh'),
        ('replace', 'Thay thế')
    ], 'Loại phát hành', default='vat', required=True)

    code = fields.Char(string="Mã", default="New", copy=False)
    invoice_ids = fields.Many2many(comodel_name='account.move', copy=False, string='DS Hóa đơn')
    line_ids = fields.One2many(
        comodel_name='invoice.not.exists.bkav.line',
        inverse_name='parent_id',
        string='Chi tiêt bán hàng'
    )
    state = fields.Selection([('new', 'Mới'),('post', 'Đã tích hợp')], copy=False)

    def genarate_code(self):
        code = '982' 
        param_code = code+'%'
        query = """ 
            SELECT code
            FROM (
                (SELECT '0000000' as code)
                UNION ALL
                (SELECT RIGHT(code,7) as code
                FROM invoice_not_exists_bkav
                WHERE code like %s
                ORDER BY code desc
                LIMIT 1)) as compu
            ORDER BY code desc LIMIT 1
        """
        self._cr.execute(query, (param_code,))
        result = self._cr.fetchall()
        for list_code in result:
            if list_code[0] == '0000000':
                code+='0000000'
            else:
                code_int = int(list_code[0])
                code+='0'*len(7-len(code_int+1))+str(code_int+1)
        return code


    def general_invoice_not_exists_bkav(self):
        move_date = datetime.utcnow().date()
        # tổng hợp hóa đơn nhanh
        query = """
            SELECT DISTINCT am.id 
            FROM sale_order so
            JOIN sale_order_line sol on sol.order_id = so.id
            JOIN sale_order_line_invoice_rel solir on solir.order_line_id = sol.id
            JOIN account_move_line aml on solir.invoice_line_id = aml.id
            JOIN account_move am on am.id = aml.move_id
            JOIN res_company r on am.company_id = r.id
            WHERE so.source_record = TRUE 
            AND (am.invoice_date <= %s)
            AND am.exists_bkav = 'f'
            AND am.state = 'posted' AND r.code = '1300'
        """
        self._cr.execute(query, ((move_date,)))
        result = self._cr.fetchall()
        nhanh_invoice_ids = self.env['account.move'].sudo().browse([idd[0] for idd in result])
        company_id = nhanh_invoice_ids[0].company_id
        invoice_bkav_ids = self.with_company(company_id).create_general_invoice(nhanh_invoice_ids, move_date)
        for invoice_bkav_id in invoice_bkav_ids:
            # invoice_bkav_id.genarate_code()
            invoice_bkav_id.create_invoice_bkav()
            invoice_bkav_id.update_invoice_status()


    def create_general_invoice(self, invoices, move_date):
        out_invoices = invoices.filtered(lambda x: x.move_type == 'out_invoice')
        refund_invoices = invoices.filtered(lambda x: x.move_type == 'out_refund')
        invoice_bkav_ids = []
        list_out_line_vals = []
        list_negative_line_vals = []
        if out_invoices or refund_invoices:
            out_line_vals = []
            negative_line_vals = []
            line_checked = []
            product_checked = []
            # Sản phẩm có cả bán và trả trong ngày
            for line in out_invoices.invoice_line_ids:
                if line.id not in line_checked:
                    product_checked.append(line.product_id.id)
                    product_line_ids = out_invoices.invoice_line_ids.filtered(
                        lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
                    refund_line_ids = refund_invoices.invoice_line_ids.filtered(
                        lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
                    line_checked += (product_line_ids + refund_line_ids).ids
                    diff_qty = sum(product_line_ids.mapped('quantity')) - sum(refund_line_ids.mapped('quantity'))
                    price_subtotal = sum(product_line_ids.mapped('price_subtotal')) - sum(
                        refund_line_ids.mapped('price_subtotal'))
                    if diff_qty > 0:
                        out_line_vals.append((0, 0, {
                            'product_id': line.product_id.id,
                            'uom_id': line.product_id.uom_id.id,
                            'quantity': diff_qty,
                            'price_unit': line.price_unit,
                            'price_subtotal': price_subtotal,
                            'taxes_id': line.tax_ids.id
                        }))
                        if len(out_line_vals) == 1000:
                            list_out_line_vals.append(out_line_vals)
                            out_line_vals = []
                    if diff_qty < 0:
                        negative_line_vals.append((0, 0, {
                            'product_id': line.product_id.id,
                            'uom_id': line.product_id.uom_id.id,
                            'quantity': diff_qty,
                            'price_unit': line.price_unit,
                            'price_subtotal': price_subtotal,
                            'taxes_id': line.tax_ids.id
                        }))
                        if len(negative_line_vals) == 1000:
                            list_negative_line_vals.append(negative_line_vals)
                            negative_line_vals = []
            # Sản phẩm chỉ có trả trong ngày
            for line in refund_invoices.invoice_line_ids.filtered(lambda x: x.product_id.id not in product_checked):
                if line.id not in line_checked:
                    refund_line_ids = refund_invoices.invoice_line_ids.filtered(
                        lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
                    line_checked += refund_line_ids.ids
                    negative_line_vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'uom_id': line.product_id.uom_id.id,
                        'quantity': -sum(refund_line_ids.mapped('quantity')),
                        'price_unit': line.price_unit,
                        'price_subtotal': -sum(refund_line_ids.mapped('price_subtotal')),
                        'taxes_id': line.tax_ids.id
                    }))
                    if len(negative_line_vals) == 1000:
                        list_negative_line_vals.append(negative_line_vals)
                        negative_line_vals = []
        if out_line_vals:
            list_out_line_vals.append(out_line_vals)
        if negative_line_vals:
            list_negative_line_vals.append(negative_line_vals)
        for out_item in list_out_line_vals:
            invoice_bkav_id = self.env['invoice.not.exists.bkav'].sudo().create({
                'code': self.genarate_code(),
                'company_id': invoices[0].company_id.id,
                'partner_id': invoices[0].partner_id.id,
                'move_date': move_date,
                'invoice_ids': [(6, 0, invoices.ids)],
                'line_ids': out_item,
            })
            invoice_bkav_ids.append(invoice_bkav_id)
        for negative_item in list_negative_line_vals:
            invoice_bkav_id = self.env['invoice.not.exists.bkav'].sudo().create({
                'code': self.genarate_code(),
                'company_id': invoices[0].company_id.id,
                'partner_id': invoices[0].partner_id.id,
                'move_date': move_date,
                'invoice_ids': [(6, 0, invoices.ids)],
                'line_ids': negative_item,
            })
            invoice_bkav_ids.append(invoice_bkav_id)
        return invoice_bkav_ids


    def update_invoice_status(self):
        for invoice in self:
            if invoice.state == 'new':
                invoice.state = 'post'
            for invoice_id in invoice.invoice_ids:
                if not invoice_id.is_general:
                    invoice_id.is_general = True
                    invoice_id.exists_bkav = True


    @api.depends('data_compare_status')
    def _compute_data_compare_status_get_values(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)


    def get_invoice_identify(self):
        invoice_form = self.invoice_form or ''
        invoice_serial = self.invoice_serial or ''
        invoice_no = self.invoice_no or ''
        return f"[{invoice_form}]_[{invoice_serial}]_[{invoice_no}]"


    def get_bkav_config(self):
        return {
            'bkav_url': self.env['ir.config_parameter'].sudo().get_param('bkav.url'),
            'partner_token': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_token'),
            'partner_guid': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_guid'),
            'cmd_addInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice'),
            'cmd_addInvoiceEdit': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit'),
            'cmd_addInvoiceEditDiscount': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit_discount'),
            'cmd_addInvoiceReplace': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_replace'),
            'cmd_updateInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.update_einvoice'),
            'cmd_deleteInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.delete_einvoice'),
            'cmd_cancelInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.cancel_einvoice'),
            'cmd_publishInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.publish_invoice'),
            'cmd_getInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_einvoice'),
            'cmd_getStatusInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_status_einvoice'),
            'cmd_downloadPDF': self.env['ir.config_parameter'].sudo().get_param('bkav.download_pdf'),
            'cmd_downloadXML': self.env['ir.config_parameter'].sudo().get_param('bkav.download_xml')
        }


    def getting_invoice_status(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_getStatusInvoice')),
            "CommandObject": self.invoice_guid,
        }
        _logger.info(f'BKAV - data get invoice status to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            self.data_compare_status = str(response.get('Object'))


    def get_bkav_data(self):
        bkav_data = []
        for invoice in self:
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(datetime.now(), datetime.now().time()))
            list_invoice_detail = []
            for line in invoice.line_ids:
                item = {
                    "ItemName": line.product_id.name,
                    "UnitName": line.uom_id.name or '',
                    "Qty": line.quantity or 0.0,
                    "Price": line.price_unit,
                    "Amount": line.price_subtotal,
                    "TaxAmount": (line.tax_amount or 0.0),
                    "ItemTypeID": 0,
                    "IsDiscount": 0,
                }
                if line.taxes_id:
                    if line.tax_ids[0].amount == 0:
                        tax_rate_id = 0
                    elif line.tax_ids[0].amount == 5:
                        tax_rate_id = 1
                    elif line.tax_ids[0].amount == 10:
                        tax_rate_id = 3
                    else:
                        tax_rate_id = 6
                    item.update({
                        "TaxRateID": tax_rate_id,
                        "TaxRate": line.tax_ids[0].amount
                    })
                list_invoice_detail.append(item)
            bkav_data.append({
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerTaxCode": invoice.partner_id.vat if invoice.partner_id.vat else '',
                    "BuyerUnitName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerAddress": invoice.partner_id.country_id.name if invoice.partner_id.country_id.name else '',
                    "BuyerBankAccount": '',
                    "PayMethodID": 1,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": invoice.company_id.email if invoice.company_id.email else '',
                    "ReceiverMobile": invoice.company_id.mobile if invoice.company_id.mobile else '',
                    "ReceiverAddress": invoice.company_id.street if invoice.company_id.street else '',
                    "ReceiverName": invoice.company_id.name if invoice.company_id.name else '',
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": invoice.company_id.currency_id.name if invoice.company_id.currency_id.name else '',
                    "ExchangeRate": 1.0,
                    "InvoiceForm": "",
                    "InvoiceSerial": "",
                    "InvoiceNo": 0,
                    "OriginalInvoiceIdentify": '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": invoice.code,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data


    def create_invoice_bkav(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        configs = self.get_bkav_config()
        _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
        data = {
            "CmdType": int(configs.get('cmd_addInvoice')),
            "CommandObject": self.get_bkav_data()
        }
        _logger.info(f'BKAV - data create invoice to BKAV: {data}')
        try:
            response = connect_bkav(data, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            result_data = json.loads(response.get('Object', []))[0]
            try:
                # ghi dữ liệu
                self.write({
                    'exists_bkav': True,
                    'invoice_guid': result_data.get('InvoiceGUID'),
                    'invoice_no': result_data.get('InvoiceNo'),
                    'invoice_form': result_data.get('InvoiceForm'),
                    'invoice_serial': result_data.get('InvoiceSerial'),
                    'invoice_e_date': datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S') if result_data.get('InvoiceDate') else None
                })
                if result_data.get('MessLog'):
                    self.message_post(body=result_data.get('MessLog'))
                self.getting_invoice_status()
                self.publish_invoice_bkav()
            except:
                self.get_invoice_bkav()


    def publish_invoice_bkav(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        configs = self.get_bkav_config()

        data = {
            "CmdType": int(configs.get('cmd_publishInvoice')),
            "CommandObject": self.invoice_guid,
        }
        # connect_bkav(data, configs)
        _logger.info(f'BKAV - data publish invoice to BKAV: {data}')
        try:
            response = connect_bkav(data, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            self.is_post_bkav = True
            self.get_invoice_bkav()


    def update_invoice_bkav(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_updateInvoice')),
            "CommandObject": self.get_bkav_data()
        }
        _logger.info(f'BKAV - data update invoice to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            raise ValidationError(response.get('Object'))
        else:
            self.getting_invoice_status()


    def get_invoice_bkav(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_getInvoice')),
            "CommandObject": self.id
        }
        _logger.info(f'BKAV - data get invoice from BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            self.message_post(body=(response.get('Object')))
        else:
            result_data = json.loads(response.get('Object', {})).get('Invoice', {})
            self.write({
                'data_compare_status': str(result_data.get('InvoiceStatusID')),
                'exists_bkav': True,
                'invoice_guid': result_data.get('InvoiceGUID'),
                'invoice_no': result_data.get('InvoiceNo'),
                'invoice_form': result_data.get('InvoiceForm'),
                'invoice_serial': result_data.get('InvoiceSerial'),
                'invoice_e_date': datetime.strptime(result_data.get('InvoiceDate').split('.')[0], '%Y-%m-%dT%H:%M:%S') if result_data.get('InvoiceDate') else None,
                'invoice_state_e': str(result_data.get('InvoiceStatusID'))
            })


    def cancel_invoice_bkav(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_cancelInvoice')),
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceGUID": self.invoice_guid,
                        "Reason": "Hủy vì sai sót"
                    },
                    "PartnerInvoiceID": self.id,
                }
            ]
        }
        _logger.info(f'BKAV - data cancel invoice to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            raise ValidationError(response.get('Object'))
        else:
            self.is_check_cancel = True
            self.getting_invoice_status()


    def delete_invoice_bkav(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        configs = self.get_bkav_config()
        data = {
            "CmdType": int(configs.get('cmd_deleteInvoice')),
            "CommandObject": [
                {
                    "Invoice": {
                        "InvoiceGUID": self.invoice_guid,
                        "Reason": "Xóa vì sai sót"
                    },
                    "PartnerInvoiceID": self.id,
                }
            ]
        }
        _logger.info(f'BKAV - data delete invoice to BKAV: {data}')
        response = connect_bkav(data, configs)
        if response.get('Status') == 1:
            raise ValidationError(response.get('Object'))


    def download_invoice_bkav(self):
        self = self.sudo()
        self = self.with_company(self.company_id)
        if not self.eivoice_file:
            configs = self.get_bkav_config()
            data = {
                "CmdType": int(configs.get('cmd_downloadPDF')),
                "CommandObject": self.invoice_guid,
            }
            _logger.info(f'BKAV - data download invoice to BKAV: {data}')
            response_action = connect_bkav(data, configs)
            if response_action.get('Status') == '1':
                self.message_post(body=(response_action.get('Object')))
            else:
                attachment_id = self.env['ir.attachment'].sudo().create({
                    'name': f"{self.invoice_no}.pdf",
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


class InvoiceNotExistsBkavLine(models.Model):
    _name = 'invoice.not.exists.bkav.line'
    _description = 'General Invoice Not Exists Bkav Line'

    parent_id = fields.Many2one('invoice.not.exists.bkav', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Float(string='Subtotal')
    tax_amount = fields.Float(string='Tax Amount')
    taxes_id = fields.Many2one('account.tax', string='Tax %', domain=[('active', '=', True)])
    origin_move_id = fields.Many2one('account.move', 'Origin move')
