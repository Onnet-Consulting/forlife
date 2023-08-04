from odoo import api, fields, models
from datetime import date, datetime, timedelta
from ...bkav_connector.models import bkav_action_return
from odoo.exceptions import ValidationError


class PosOrderReturn(models.Model):
    _inherit = "pos.order"

    exists_bkav_return = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav_return = fields.Boolean(default=False, copy=False, string="Đã ký HĐ trên BKAV")
    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e_return = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status_return', store=True,copy=False)
    invoice_guid_return = fields.Char('GUID HDDT', copy=False)
    invoice_no_return = fields.Char('Số HDDT', copy=False)
    invoice_form_return = fields.Char('Mẫu số HDDT', copy=False)
    invoice_serial_return = fields.Char('Ký hiệu HDDT', copy=False)
    invoice_e_date_return = fields.Date('Ngày HDDT', copy=False)
    data_compare_status_return = fields.Selection([('1', 'Mới tạo'),
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

    eivoice_file_return = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)
    issue_invoice_type = fields.Selection([
        ('vat', 'GTGT'),
        ('adjust', 'Điều chỉnh'),
        ('replace', 'Thay thế')
    ], 'Loại phát hành', default='adjust', required=True)
    origin_move_id = fields.Many2one('pos.order', 'Hóa đơn gốc')
    
    
    def _get_promotion_in_pos_return(self):
        list_invoice_detail = []
        if self.total_point != 0:
            line_invoice = {
                "ItemName": "Tích điểm",
                "UnitName": 'Điểm',
                "Qty": abs(self.total_point),
                "Price": 0,
                "Amount": 0,
                "TaxAmount": 0,
                "IsDiscount": 1,
                "ItemTypeID": 0,
            }
            list_invoice_detail.append(line_invoice)
        
        use_point = {}
        rank_total = {}
        for promotion_id in self.lines:
            if promotion_id.is_promotion and promotion_id.promotion_type == 'point':
                vat = 0
                if promotion_id.tax_ids:
                    vat = promotion_id.tax_ids[0].amount
                if vat not in list(use_point.keys()):
                    use_point.update({
                        vat:promotion_id.subtotal_paid,
                    })
                else:
                    use_point[vat] += promotion_id.subtotal_paid
            if promotion_id.is_promotion and promotion_id.promotion_type == 'card':
                vat = 0
                if promotion_id.tax_ids:
                    vat = promotion_id.tax_ids[0].amount
                if vat not in list(rank_total.keys()):
                    rank_total.update({
                        vat:promotion_id.subtotal_paid,
                    })
                else:
                    rank_total[vat] += promotion_id.subtotal_paid
        for vat, value in use_point.items():
            value_not_tax = round(abs(value)/(1+vat/100))
            line_invoice = {
                "ItemName": "Tiêu điểm",
                "UnitName": 'Điểm',
                "Qty": abs(value/1000),
                "Price": 1000/(1+vat/100),
                "TaxAmount": abs(value - value_not_tax),
                "IsDiscount": 1,
                "ItemTypeID": 0,
            }
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
            line_invoice.update({
                "TaxRateID": tax_rate_id,
                "TaxRate": vat
            })
            list_invoice_detail.append(line_invoice)

        for vat, value in rank_total.items():
            value_not_tax = round(abs(value)/(1+vat/100))
            line_invoice = {
                "ItemName": "Chiết khấu hạng thẻ",
                "UnitName": 'Đơn vị',
                "Qty": 1,
                "Price": abs(value_not_tax),
                "TaxAmount": abs(value - value_not_tax),
                "IsDiscount": 1,
                "ItemTypeID": 0,
            }
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
            line_invoice.update({
                "TaxRateID": tax_rate_id,
                "TaxRate": vat
            })
            list_invoice_detail.append(line_invoice)
        return list_invoice_detail


    def get_bkav_data_pos_return(self):
        bkav_data = []
        for invoice in self:       
            invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(invoice.date_order,datetime.now().time())) 
            list_invoice_detail = []
            for line in invoice.lines.filtered(lambda x: x.refunded_orderline_id != False):
                #SP KM k đẩy BKAV
                if line.is_promotion or line.product_id.voucher or line.product_id.is_product_auto or line.product_id.is_voucher_auto:
                    continue
                price_subtotal = line.price_subtotal
                price_subtotal_incl = line.price_subtotal_incl
                sublines = invoice.lines.filtered(lambda l: l.is_promotion == True and l.promotion_type not in ('point','card') and l.product_src_id.id == line.id)
                for l in sublines:
                    price_subtotal += l.price_subtotal
                    price_subtotal_incl += l.price_subtotal_incl
                price_bkav = round(price_subtotal/line.qty)
                vat, tax_rate_id = self._get_vat_line_bkav(line)
                itemname = line.product_id.name
                if line.is_reward_line:
                    itemname += '(Hàng tặng khuyến mại không thu tiền)'
                item = {
                    "ItemName": itemname,
                    "UnitName": line.product_uom_id.name or '',
                    "Qty": abs(line.qty),
                    "Price": price_bkav,
                    "Amount": price_subtotal,
                    "TaxAmount": (price_subtotal_incl - price_subtotal or 0.0),
                    "ItemTypeID": 0,
                    "DiscountRate": line.discount/100,
                    "DiscountAmount": round(line.price_subtotal/(1+line.discount/100) * line.discount/100),
                    "IsDiscount": 1 if line.is_promotion else 0
                }
                item.update({
                    "TaxRateID": tax_rate_id,
                    "TaxRate": vat
                })
                if invoice.issue_invoice_type == 'adjust':
                    item['IsIncrease'] = 0 if (invoice.refunded_order_ids.ids) else 1
                list_invoice_detail.append(item)
            #Them cac SP khuyen mai
            list_invoice_detail.extend(self._get_promotion_in_pos())

            BuyerName = invoice.partner_id.name if invoice.partner_id.name else ''
            # if invoice.invoice_info_company_name:
            #     BuyerName = invoice.invoice_info_company_name

            BuyerTaxCode =invoice.partner_id.vat or '' if invoice.partner_id.vat else ''
            if invoice.invoice_info_tax_number:
                BuyerTaxCode = invoice.invoice_info_tax_number

            BuyerUnitName = invoice.partner_id.name if invoice.partner_id.name else ''
            if invoice.invoice_info_company_name:
                BuyerUnitName = invoice.invoice_info_company_name

            BuyerAddress = invoice.partner_id.contact_address_complete if invoice.partner_id.contact_address_complete else ''
            if invoice.invoice_info_address:
                BuyerAddress = invoice.invoice_info_address

            bkav_data.append({
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": BuyerName,
                    "BuyerTaxCode": BuyerTaxCode,
                    "BuyerUnitName": BuyerUnitName,
                    "BuyerAddress": BuyerAddress,
                    "BuyerBankAccount": '',
                    "PayMethodID": 3,
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
                    "OriginalInvoiceIdentify": invoice.origin_move_id.get_invoice_identify() if invoice.issue_invoice_type in ('adjust', 'replace') else '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": invoice.pos_reference,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data


    def _check_info_before_bkav_return(self):
        if self.is_post_bkav_store:
            return True
        if not self.is_general:
            return True
        if self.issue_invoice_type != 'vat':
            if not self.origin_move_id:
                raise ValidationError('Vui lòng chọn hóa đơn gốc đã được phát hành để điều chỉnh/thay thế')
            if not self.origin_move_id.exists_bkav:
                raise ValidationError('Hóa đơn gốc chưa tồn tại trên hệ thống HDDT BKAV! Vui lòng về đơn gốc kiểm tra!')
            return True
        return False
    
    @api.depends('data_compare_status_return')
    def _compute_data_compare_status_return(self):
        for rec in self:
            rec.invoice_state_e_return = dict(self._fields['data_compare_status_return'].selection).get(rec.data_compare_status_return)


    def get_invoice_identify_return(self):
        return bkav_action_return.get_invoice_identify(self)

    def get_invoice_status_return(self):
        return bkav_action_return.get_invoice_status(self)
    
    def create_invoice_bkav_return(self):
        if not self._check_info_before_bkav_return():
            return
        data = self.get_bkav_data_pos_return()
        origin_id = self.origin_move_id
        is_publish = False
        issue_invoice_type = self.issue_invoice_type
        return bkav_action_return.create_invoice_bkav(self,data,is_publish,origin_id,issue_invoice_type)


    def update_invoice_bkav_return(self):
        if not self._check_info_before_bkav_return():
            return
        data = self.get_bkav_data_pos_return()
        return bkav_action_return.update_invoice_bkav(self,data)
    
    def publish_invoice_bkav_return(self):
        return bkav_action_return.publish_invoice_bkav(self)

    def get_invoice_bkav_return(self):
        return bkav_action_return.get_invoice_bkav(self)

    def cancel_invoice_bkav_return(self):
        return bkav_action_return.cancel_invoice_bkav(self)

    def delete_invoice_bkav_return(self):
        return bkav_action_return.delete_invoice_bkav(self)

    def download_invoice_bkav_return(self):
        return bkav_action_return.download_invoice_bkav(self)

    def unlink(self):
        for item in self:
            item.delete_invoice_bkav_return()
        return super(PosOrderReturn, self).unlink()
    
    
