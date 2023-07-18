from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError
import logging
import json
_logger = logging.getLogger(__name__)
disable_create_function = False
from ...bkav_connector.models.bkav_connector import connect_bkav

class SummaryAccountMovePos(models.Model):
    _inherit = 'summary.account.move.pos'

    def get_bkav_data(self, data, cmd_type=None):
        bkav_data = []
        for invoice in data:
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(invoice.invoice_date,
                                                                                       datetime.now().time())) if invoice.invoice_date else fields.Datetime.context_timestamp(
                invoice, datetime.now())
            list_invoice_detail = []
            for line in invoice.line_ids:
                item = {
                    "ItemName": (line.product_id.name or line.name) if (
                            line.product_id.name or line.name) else '',
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": line.quantity or 0.0,
                    "Price": line.price_unit * (1 - line.discount / 100),
                    "Amount": line.price_subtotal,
                    "TaxRateID": 3,
                    "TaxRate": 10,
                    "TaxAmount": line.tax_amount or 0.0,
                    "ItemTypeID": 0,
                    # "IsDiscount": 1 if line.promotions else 0
                }
                # if invoice.issue_invoice_type == 'edit':
                    # kiểm tra hóa đơn gốc
                    # gốc là out_invoice => điều chỉnh giảm
                    # gốc là out_refund => điều chỉnh tăng
                #     item['IsIncrease'] = invoice.origin_move_id.move_type != 'out_invoice'
                list_invoice_detail.append(item)
            invoice_json = {
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerTaxCode": invoice.partner_id.vat if invoice.partner_id.vat else '',
                    "BuyerUnitName": invoice.partner_id.name if invoice.partner_id.name else '',
                    "BuyerAddress": invoice.partner_id.country_id.name if invoice.partner_id.country_id.name else '',
                    "BuyerBankAccount": '321312434535453',
                    "PayMethodID": 1,
                    "ReceiveTypeID": 3,
                    "ReceiverEmail": invoice.company_id.email if invoice.company_id.email else '',
                    "ReceiverMobile": invoice.company_id.mobile if invoice.company_id.mobile else '',
                    "ReceiverAddress": invoice.company_id.street if invoice.company_id.street else '',
                    "ReceiverName": invoice.company_id.name if invoice.company_id.name else '',
                    "Note": "Hóa đơn mới tạo",
                    "BillCode": "",
                    "CurrencyID": self.env.company.currency_id.name if self.env.company.currency_id.name else '',
                    "ExchangeRate": 1.0,
                    "InvoiceForm": "",
                    "InvoiceSerial": "",
                    "InvoiceNo": 0,
                    # "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in
                    # ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": invoice.id,
                "ListInvoiceDetailsWS": list_invoice_detail
            }
            if cmd_type == 124:
                OriginalInvoiceIdentify = invoice.source_einvoice
                if not invoice.source_invoice:
                    OriginalInvoiceIdentify = "[1]_[C23TAC]_[153]"
                invoice_json["Invoice"].update({
                    "Reason": f"Điều chỉnh Hoá đơn {invoice.source_einvoice}",
                    "OriginalInvoiceIdentify": OriginalInvoiceIdentify
                })
            bkav_data.append(invoice_json)
        return bkav_data

    def get_bkav_config(self):
        return {
            'bkav_url': self.env['ir.config_parameter'].sudo().get_param('bkav.url'),
            'partner_token': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_token'),
            'partner_guid': self.env['ir.config_parameter'].sudo().get_param('bkav.partner_guid'),
            'cmd_addInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice'),
            'cmd_addInvoiceEdit': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_edit'),
            'cmd_addInvoiceEditDiscount': self.env['ir.config_parameter'].sudo().get_param(
                'bkav.add_einvoice_edit_discount'),
            'cmd_addInvoiceReplace': self.env['ir.config_parameter'].sudo().get_param('bkav.add_einvoice_replace'),
            'cmd_updateInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.update_einvoice'),
            'cmd_deleteInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.delete_einvoice'),
            'cmd_cancelInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.cancel_einvoice'),
            'cmd_publishInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.publish_einvoice'),
            'cmd_getInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_einvoice'),
            'cmd_getStatusInvoice': self.env['ir.config_parameter'].sudo().get_param('bkav.get_status_einvoice'),
            'cmd_downloadPDF': self.env['ir.config_parameter'].sudo().get_param('bkav.download_pdf'),
            'cmd_downloadXML': self.env['ir.config_parameter'].sudo().get_param('bkav.download_xml')
        }

    def download_e_invoice(self):
        if self.eivoice_file:
            return {
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&name=%s&download=true"
                       % (self.eivoice_file.id, self.eivoice_file.name),
                'target': 'self',
            }
        else:
            raise ValidationError(_("Don't have any eInvoice in this invoice. Please check again!"))

    def create_invoice_bkav(self, cmd_type, data_invoice):
        configs = self.get_bkav_config()
        _logger.info("----------------Start Sync orders from BKAV-INVOICE-E --------------------")
        data = {
            "CmdType": cmd_type,
            "CommandObject": data_invoice
        }
        _logger.info(f'BKAV - data create invoice to BKAV: {data}')
        try:
            response = connect_bkav(data, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            print(response.get('Object'))
        else:
            result_data = json.loads(response.get('Object', []))[0]
            try:
                # ghi dữ liệu
                return {
                    'exists_bkav': True,
                    'is_post_bkav': True,
                    'partner_invoice_id': result_data.get('PartnerInvoiceID'),
                    'invoice_guid': result_data.get('InvoiceGUID'),
                    'invoice_no': result_data.get('InvoiceNo'),
                    'invoice_form': result_data.get('InvoiceForm'),
                    'invoice_serial': result_data.get('InvoiceSerial'),
                    'invoice_e_date': datetime.strptime(result_data.get('SignedDate'), '%Y-%m-%dT%H:%M:%S.%f') - timedelta(
                        hours=7) if result_data.get('SignedDate') else None
                }
            except Exception as ex:
                _logger.error(f'BKAV connect_bkav: {ex}')
                return False

    def collect_bills_the_end_day(self):
        synthetic, adjusted = self.get_val_synthetic_account()
        self.summary_post_bkav(synthetic, 101)
        self.summary_post_bkav(adjusted, 124)

        today = date.today() - timedelta(days=1)
        summary_adjusted_pos = self.env['summary.adjusted.invoice.pos'].search([
            ('invoice_date', '=', today)
        ])
        moves = self.env['account.move']
        invoices = moves.search([('company_id', '=', self.env.company.id),
                                 ('move_type', 'in', ('out_invoice', 'out_refund')),
                                 ('is_post_bkav', '=', False),
                                 ('pos_order_id', '!=', False),
                                 ('invoice_date', '<=', today)])
        for inv in invoices:
            inv.write({
                'is_post_bkav': True,
                'invoice_no': summary_adjusted_pos.number_bill,
                'invoice_serial': summary_adjusted_pos.account_einvoice_serial,
                'invoice_e_date': summary_adjusted_pos.einvoice_date,
                'invoice_form': summary_adjusted_pos.invoice_form,
                'invoice_guid': summary_adjusted_pos.invoice_guid
            })

    def summary_post_bkav(self, data, cmd_type=None):
        gui_id_list = []
        for item in data:
            item_bkav = self.get_bkav_data(item, cmd_type)

            einvoice = self.create_invoice_bkav(cmd_type, item_bkav)
            gui_id_list.append(einvoice.get('invoice_guid'))
            item.number_bill = '[{}]_[{}]_[{}]'.format(einvoice.get('invoice_form'),
                                                       einvoice.get('invoice_serial'),
                                                       einvoice.get('invoice_no'))
            item.code = item.number_bill
            item.invoice_guid = einvoice.get('invoice_guid')
            item.invoice_form = einvoice.get('invoice_form')
            item.einvoice_date = einvoice.get('invoice_e_date')
            item.account_einvoice_serial = einvoice.get('invoice_serial')
            item.partner_invoice_id = einvoice.get('partner_invoice_id')

        self.sign_invoice_bkav(gui_id_list, data)

    def sign_invoice_bkav(self, gui_id_list, records):
        configs = self.get_bkav_config()
        invoice_guid_list = []
        for gui_id in gui_id_list:
            invoice_guid_list.append({
                "InvoiceGUID": gui_id
            })
        body = {
            "CmdType": 206,
            "CommandObject": invoice_guid_list
        }
        try:
            response = connect_bkav(body, configs)
        except Exception as ex:
            _logger.error(f'BKAV connect_bkav: {ex}')
            return False
        if response.get('Status') == 1:
            _logger.error(response.get('Object'), "nvgiang")
        else:
            for item in records:
                item.einvoice_status = 'sign'
                item.state = 'posted'
