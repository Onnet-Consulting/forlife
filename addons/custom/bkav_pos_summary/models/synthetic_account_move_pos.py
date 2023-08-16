# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from ...bkav_connector.models import bkav_action


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
    
    exists_bkav = fields.Boolean(default=False, copy=False, string="Đã tồn tại trên BKAV")
    is_post_bkav = fields.Boolean(default=False, copy=False, string="Đã ký HĐ trên BKAV")
    invoice_guid = fields.Char('GUID HDDT')
    invoice_no = fields.Char('Số hóa đơn')
    invoice_form = fields.Char('Mẫu số HDDT')
    invoice_serial = fields.Char('Mẫu số - Ký hiệu hóa đơn')
    invoice_e_date = fields.Date(string="Ngày phát hành")
    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status', store=True,
                                  copy=False)
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
    partner_invoice_id = fields.Integer(string='Số hóa đơn')
    eivoice_file = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)

    total_point = fields.Integer(
        string='Total Point', 
        readonly=True, 
        compute='_compute_total_point', 
        store=True,
        help='Điểm cộng đơn hàng + Điểm sự kiện đơn + Điểm cộng + Điểm sự kiện'
    )

    line_discount_ids = fields.One2many('synthetic.account.move.pos.line.discount', compute="_compute_line_discount")

    line_adjusted_ids = fields.One2many('summary.adjusted.invoice.pos.line', 'synthetic_id')

    discount_ids = fields.One2many('synthetic.account.move.pos.line.discount', compute="_compute_line_discount")

    @api.model
    def _compute_line_discount(self):
        model_line_discount = self.env["synthetic.account.move.pos.line.discount"]
        for r in self:
            r.line_discount_ids = model_line_discount.search([
                ('synthetic_id', '=', r.id)
            ])
            r.discount_ids = model_line_discount.search([
                ('synthetic_ids', 'in', [r.id]),
                ('synthetic_line_id', '=', False),
                ('store_id', '=', r.store_id.id)
            ])

    @api.depends('data_compare_status')
    def _compute_data_compare_status(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)

    @api.depends('line_ids.invoice_ids')
    def _compute_total_point(self):
        for res in self:
            total_point = 0
            exists_pos = {}
            for pos in res.line_ids.invoice_ids:
                if not exists_pos.get(pos.id):
                    exists_pos[pos.id] = True
                    total_point += pos.get_total_point()

            res.total_point = abs(total_point)


    def get_invoice_identify(self):
        return bkav_action.get_invoice_identify(self)



    def action_download_view_e_invoice(self):
        return bkav_action.download_invoice_bkav(self)

    def get_vat(self, line):
        vat = 0
        if line.tax_ids:
            if len(line.tax_ids) == 1:
                vat = line.tax_ids[0].amount
            else:
                tax_amount = 1
                for tax in line.tax_ids:
                    tax_amount = tax_amount * tax.amount
                vat = tax_amount / 100

        if vat == 0:
            tax_rate_id = 1
        elif vat == 5:
            tax_rate_id = 2
        elif vat == 3.5:
            tax_rate_id = 7
        elif vat == 7:
            tax_rate_id = 8
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

    def get_promotion(self, ln):
        list_invoice_details_ws = []
        line_discount_ids = self.env["synthetic.account.move.pos.line.discount"].search([
            ('synthetic_id', '=', ln.id)
        ])
        if ln.total_point > 0:
            line_invoice = {
                "ItemName": "Tích điểm",
                "UnitName": 'Điểm',
                "Qty": ln.total_point,
                "Price": 0,
                "Amount": 0,
                "TaxAmount": 0,
                "IsDiscount": 1,
                "ItemTypeID": 0,
                "TaxRateID": 1,
                "TaxRate": 0,
            }
            list_invoice_details_ws.append(line_invoice)

        if line_discount_ids:
            line_discount_point_ids = line_discount_ids.filtered(lambda r: r.promotion_type == 'point')
            if line_discount_point_ids:
                line_discount_point_taxs = {}
                for line in line_discount_point_ids:
                    line_pk = line.line_pk
                    if line_discount_point_taxs.get(line_pk):
                        row = line_discount_point_taxs[line_pk]
                        row["Qty"] += abs(line.price_unit_incl)/1000
                        row["Amount"] += abs(line.price_unit)
                        row["TaxAmount"] += abs(line.tax_amount)
                        line_discount_point_taxs[line_pk] = row
                    else:
                        price = 1000/line.get_tax_amount()

                        vat, tax_rate_id = self.get_vat(line)
                        line_discount_point_taxs[line_pk] = {
                            "ItemName": "Tiêu điểm",
                            "UnitName": 'Điểm',
                            "Qty": abs(line.price_unit_incl)/1000,
                            "Price": round(price, 2),
                            "Amount": abs(line.price_unit),
                            "TaxAmount": abs(line.tax_amount),
                            "IsDiscount": 1,
                            "ItemTypeID": 0,
                            "TaxRateID": tax_rate_id,
                            "TaxRate": vat,
                        }
                list_invoice_details_ws.extend(list(line_discount_point_taxs.values()))

            line_discount_card_ids = line_discount_ids.filtered(lambda r: r.promotion_type == 'card')
            if line_discount_card_ids:
                line_discount_card_taxs = {}
                for line in line_discount_card_ids:
                    line_pk = line.line_pk
                    if line_discount_card_taxs.get(line_pk):
                        row = line_discount_card_taxs[line_pk]
                        row["Price"] += abs(line.price_unit)
                        row["Amount"] += abs(line.price_unit)
                        row["TaxAmount"] += abs(line.tax_amount)
                        line_discount_card_taxs[line_pk] = row
                    else:
                        vat, tax_rate_id = self.get_vat(line)
                        line_discount_card_taxs[line_pk] = {
                            "ItemName": "Chiết khấu hạng thẻ",
                            "UnitName": '',
                            "Price": abs(line.price_unit),
                            "Amount": abs(line.price_unit),
                            "TaxAmount": abs(line.tax_amount),
                            "IsDiscount": 1,
                            "ItemTypeID": 0,
                            "TaxRateID": tax_rate_id,
                            "TaxRate": vat,
                        }
        
                list_invoice_details_ws.extend(list(line_discount_card_taxs.values()))
        return list_invoice_details_ws

    def get_bkav_data_pos(self):
        bkav_invoices = []
        for ln in self:
            invoice_date = fields.Datetime.context_timestamp(ln, datetime.combine(ln.invoice_date, datetime.now().time()))
            ln_invoice = {
                "Invoice": {
                    "InvoiceTypeID": 1,
                    "InvoiceDate": str(invoice_date).replace(' ', 'T'),
                    "BuyerName": 'Khách lẻ',
                    "BuyerTaxCode": '',
                    "BuyerUnitName": 'Khách hàng không lấy hoá đơn',
                    "BuyerAddress":  str(ln.partner_id.street).strip() if ln.partner_id.street else '',
                    "BuyerBankAccount": "",
                    "PayMethodID": 3,
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
                },
                "ListInvoiceDetailsWS": [],
                "PartnerInvoiceID": 0,
                "PartnerInvoiceStringID": ln.code,
            }
            for line in ln.line_ids:
                if not line.product_id:
                    continue
                if line.product_id.voucher or line.product_id.is_voucher_auto or line.product_id.is_product_auto:
                    continue
                
                product_tmpl_id =  line.product_id.product_tmpl_id
                if product_tmpl_id.voucher or product_tmpl_id.is_voucher_auto or product_tmpl_id.is_product_auto:
                    continue
                    
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

            ln_invoice["ListInvoiceDetailsWS"].extend(self.get_promotion(ln))
            bkav_invoices.append(ln_invoice)
        return bkav_invoices

    def create_an_invoice(self):
        for line in self:
            # try:
            bkav_invoice_data = line.get_bkav_data_pos()
            bkav_action.create_invoice_bkav(line, bkav_invoice_data, is_publish=True)
            # except Exception as e:
            #     line.message_post(body=str(e))
            

    def get_invoice_bkav(self):
        bkav_action.get_invoice_bkav(self)
        
class SyntheticAccountMovePosLine(models.Model):
    _name = 'synthetic.account.move.pos.line'

    line_pk = fields.Char('Line primary key')
    synthetic_id = fields.Many2one('synthetic.account.move.pos')
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    barcode = fields.Char(related='product_id.barcode')
    description = fields.Char('Mô tả')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    quantity = fields.Float('Số lượng')
    adjusted_quantity = fields.Float('Số lượng điều chỉnh')
    remaining_quantity = fields.Float('Số lượng còn lại')
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="Đơn vị")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    x_free_good = fields.Boolean('Hàng tặng')
    discount = fields.Float('% chiết khấu')
    discount_amount = fields.Monetary('Số tiền chiết khấu')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="_compute_amount")
    price_subtotal = fields.Monetary('Thành tiền trước thuế', compute="_compute_amount")
    amount_total = fields.Monetary('Thành tiền', compute="_compute_amount")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    invoice_ids = fields.Many2many('pos.order', string='Hóa đơn')
    summary_line_id = fields.Many2one('summary.account.move.pos.line')
    return_line_id = fields.Many2one('summary.account.move.pos.return.line')
    invoice_date = fields.Date(string='Date', related="synthetic_id.invoice_date", store=True)
    exists_bkav = fields.Boolean(copy=False, string="Đã tồn tại trên BKAV", related="synthetic_id.exists_bkav")
    line_ids = fields.One2many('synthetic.account.move.pos.line.discount', 'synthetic_line_id')


    @api.depends('tax_ids', 'price_unit_incl', 'price_unit')
    def _compute_amount(self):
        for r in self:
            tax_results = r.tax_ids.compute_all(r.price_unit_incl, quantity=r.quantity)
            r.price_subtotal = tax_results["total_excluded"]
            r.amount_total = tax_results["total_included"]
            r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"]


class SyntheticAccountMovePosLineDiscount(models.Model):
    _name = 'synthetic.account.move.pos.line.discount'

    line_pk = fields.Char('Line primary key')
    synthetic_line_id = fields.Many2one('synthetic.account.move.pos.line')
    synthetic_id = fields.Many2one('synthetic.account.move.pos',related="synthetic_line_id.synthetic_id")
    price_unit = fields.Float('Đơn giá')
    price_unit_incl = fields.Float('Đơn giá sau thuế')
    tax_ids = fields.Many2many('account.tax', string='Thuế')
    tax_amount = fields.Monetary('Tổng tiền thuế', compute="_compute_amount")
    amount_total = fields.Monetary('Thành tiền')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    promotion_type = fields.Selection(
        selection=[
            ('point', 'Point'),
            ('card', 'Card'),
        ],
        string='Promotion Type', index=True, readonly=True
    )
    synthetic_ids = fields.Many2many('synthetic.account.move.pos', string='Hóa đơn bù trừ', relation='synthetic_account_move_pos_card_point_line_discount_rel')
    bkav_synthetic_id = fields.Many2one('synthetic.account.move.pos', string='Hóa đơn bù trừ')
    store_id = fields.Many2one('store')


    def get_tax_amount(self):
        return (1 + sum(self.tax_ids.mapped("amount"))/100)

    @api.depends('tax_ids', 'price_unit_incl')
    def _compute_amount(self):
        for r in self:
            if r.tax_ids:
                tax_results = r.tax_ids.compute_all(r.price_unit_incl)
                r.tax_amount = tax_results["total_included"] - tax_results["total_excluded"] 
            else:
                r.tax_amount = 0

