from odoo import api, fields, models
from datetime import date, datetime, timedelta
from ...bkav_connector.models import bkav_action


class PosOrder(models.Model):
    _inherit = "pos.order"

    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav = fields.Boolean(default=False, copy=False, string="Đã ký HĐ trên BKAV")
    is_check_cancel = fields.Boolean(default=False, copy=False, string="Đã hủy")
    is_general = fields.Boolean(default=False, copy=False, string="Đã chạy tổng hợp cuối ngày")
    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status', store=True, copy=False)
    invoice_guid = fields.Char('GUID HDDT', copy=False)
    invoice_no = fields.Char('Số HDDT', copy=False)
    invoice_form = fields.Char('Mẫu số HDDT', copy=False)
    invoice_serial = fields.Char('Ký hiệu HDDT', copy=False)
    invoice_e_date = fields.Date('Ngày HDDT', copy=False)
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
    exists_total_point = fields.Boolean(default=False, copy=False, string="Exists total point")

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['issue_invoice_type'] = 'adjust'
        default['origin_move_id'] = self.id
        return super().copy(default)

    def _get_vat_line_bkav(self, line):
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
    
    
    def _get_promotion_in_pos(self):
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
            value_not_tax = round(value/(1+vat/100))
            line_invoice = {
                "ItemName": "Tiêu điểm",
                "UnitName": 'Điểm',
                "Qty": abs(value/1000),
                "Price": round(1000/(1+vat/100)),
                "Amount": abs(value_not_tax),
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
            value_not_tax = round(value/(1+vat/100))
            line_invoice = {
                "ItemName": "Chiết khấu hạng thẻ",
                "UnitName": 'Đơn vị',
                "Qty": 0,
                "Price": abs(value_not_tax),
                "Amount": abs(value_not_tax),
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


    def get_bkav_data_pos(self):
        bkav_data = []
        for invoice in self:
            if datetime.now().time().hour >= 17:
                invoice_date = datetime.combine(invoice.date_order, (datetime.now() - timedelta(hours=17)).time())
            else:
                invoice_date = datetime.combine(invoice.date_order, (datetime.now() + timedelta(hours=7)).time())       
            # invoice_date = fields.Datetime.context_timestamp(invoice, datetime.combine(invoice.date_order,datetime.now().time())) 
            list_invoice_detail = []
            for line in invoice.lines.filtered(lambda x: not x.refunded_orderline_id):
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
                    # "DiscountRate": line.discount/100,
                    # "DiscountAmount": round(line.price_subtotal/(1+line.discount/100) * line.discount/100),
                    "IsDiscount": 1 if line.is_promotion else 0
                }
                item.update({
                    "TaxRateID": tax_rate_id,
                    "TaxRate": vat
                })
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
                    "OriginalInvoiceIdentify": '',  # dùng cho hóa đơn điều chỉnh
                },
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": invoice.pos_reference,
                "ListInvoiceDetailsWS": list_invoice_detail
            })
        return bkav_data


    def _check_info_before_bkav(self):
        if not self.is_post_bkav_store:
            return False
        if self.is_general:
            return False
        return True

    @api.depends('data_compare_status')
    def _compute_data_compare_status(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)

    def get_invoice_identify(self):
        return bkav_action.get_invoice_identify(self)

    def get_invoice_status(self):
        return bkav_action.get_invoice_status(self)
    
    def create_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        data = self.get_bkav_data_pos()
        origin_id = False
        is_publish = False
        if self._context.get('is_publish'):
            is_publish = True
        issue_invoice_type = 'vat'
        return bkav_action.create_invoice_bkav(self,data,is_publish,origin_id,issue_invoice_type)
    
    def publish_invoice_bkav(self):
        return bkav_action.publish_invoice_bkav(self)
    
    def create_publish_invoice_bkav(self):
        return self.with_context({'is_publish': True}).create_invoice_bkav()

    def get_invoice_bkav(self):
        return bkav_action.get_invoice_bkav(self)
    
    def update_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        data = self.get_bkav_data_pos()
        return bkav_action.update_invoice_bkav(self,data)

    def cancel_invoice_bkav(self):
        return bkav_action.cancel_invoice_bkav(self)

    def delete_invoice_bkav(self):
        return bkav_action.delete_invoice_bkav(self)

    def download_invoice_bkav(self):
        return bkav_action.download_invoice_bkav(self)

    def unlink(self):
        for item in self:
            item.delete_invoice_bkav()
        return super(PosOrder, self).unlink()
    
    
