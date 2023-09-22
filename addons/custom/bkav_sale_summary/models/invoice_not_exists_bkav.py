# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from ...bkav_connector.models import bkav_action


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
    origin_move_id = fields.Many2one('invoice.not.exists.bkav', 'Hóa đơn gốc')

    code = fields.Char(string="Mã", default="New", copy=False)
    invoice_ids = fields.Many2many(comodel_name='account.move', copy=False, string='DS Hóa đơn')
    line_ids = fields.One2many(
        comodel_name='invoice.not.exists.bkav.line',
        inverse_name='parent_id',
        string='Chi tiêt bán hàng'
    )
    state = fields.Selection([('new', 'Mới'),('post', 'Đã tích hợp')], copy=False)

    def genarate_code(self, table_name='invoice_not_exists_bkav', default_code=None):
        code = '982' 
        if not default_code:
            param_code = code+'%'
            query = """ 
                SELECT code
                FROM (
                    (SELECT '0000000' as code)
                    UNION ALL
                    (SELECT RIGHT(code,7) as code
                    FROM {table}
                    WHERE code like %s
                    ORDER BY code desc
                    LIMIT 1)) as compu
                ORDER BY code desc LIMIT 1
            """.format(table=table_name)
            self._cr.execute(query, (param_code,))
            result = self._cr.fetchall()
            for list_code in result:
                if list_code[0] == '0000000':
                    code+='0000001'
                else:
                    # code_int = int(list_code[0])
                    # code+='0'*len(7-len(code_int+1))+str(code_int+1)
                    code_int = int(list_code[0])
                    code +='0'*(7-len(str(code_int+1)))+str(code_int+1)
        else:
            list_code = default_code.replace(code, '')
            code_int = int(list_code)
            code +='0'*(7-len(str(code_int+1)))+str(code_int+1)

        return code


    def genarate_pos_code(self, typ='B', order=None, index=0):
        location = order.x_location_id
        today = datetime.strftime(datetime.now(), '%d%m%Y')
        code = f"{typ}O{location.warehouse_id.code}{today}"
        code += '0'*(3-len(str(index+1)))+str(index+1)
        return code

    def get_pk_tax(self, line):
        tax_ids = []
        if line.tax_ids:
            for tax_id in line.tax_ids:
                tax_ids.append(str(tax_id.id))
        return "_".join(tax_ids)

    def get_pk_line_discount_tax(self, line):
        tax_ids = []
        if line.tax_id:
            for tax_id in line.tax_id:
                tax_ids.append(str(tax_id.id))
        else:
            tax_ids.append(str(0))

        return "_".join(tax_ids)

    def get_pk_synthetic(self, line):
        pk = f"{line.product_id.barcode}_{float(abs(line.price_unit_incl))}_{self.get_pk_tax(line)}"
        return pk

    def get_pk_synthetic_line_discount(self, line):
        pk = f"{self.get_pk_line_discount_tax(line)}"
        return pk

    def get_line_discount_detail(self, line):
        price_unit = line.tax_id.compute_all(line.value)['total_excluded']
        item = {
            "line_pk": self.get_pk_synthetic_line_discount(line),
            "price_unit": price_unit,
            "price_unit_incl": line.value,
            "tax_ids": line.tax_id.ids,
            "promotion_type": line.promotion_type,
            "amount_total": line.value,
        }
        return item

    def get_line_discount(self, line):
        line_discount_details = line.move_id.promotion_ids.filtered(
            lambda r: r.product_id.id == line.product_id.id \
            and r.promotion_type in ['vip_amount']
        )
        items = []
        if line_discount_details:
            for line_discount_detail in line_discount_details:
                item = self.get_line_discount_detail(line_discount_detail)
                items.append((0,0,item))
        return items

    def get_move_line(self, line):
        line_discount_item = self.get_line_discount(line)
        order_lines = line.sale_line_ids
        item = {
            "product_id": line.product_id.id,
            "quantity": line.quantity,
            "price_unit": line.price_unit_excl,
            "price_unit_incl": line.price_unit_incl,
            "x_free_good": order_lines[0].x_free_good if order_lines else False,
            "invoice_ids": [line.move_id.id],
            "tax_ids": line.tax_ids.ids,
            "line_ids": line_discount_item,
        }
        return item


    def include_line_by_product_and_price_bkav(self, move_lines):
        items = {}
        order = None
        if move_lines:
            if not order:
                order = move_lines.sale_line_ids.order_id[0]

            for line in move_lines:
                if not line.product_id or line.product_id.product_tmpl_id.product_type == 'service':
                    continue

                # sale_order = line.order_id


                pk = self.get_pk_synthetic(line)
                item = self.get_move_line(line)
                item["line_pk"] = pk
                if items.get(pk):
                    row = items[pk]
                    row["quantity"] += item["quantity"]
                    row["invoice_ids"].extend(item["invoice_ids"])
                    row["invoice_ids"] = list(set(row["invoice_ids"]))
                    row["line_ids"].extend(item["line_ids"])
                    items[pk] = row
                else:
                    items[pk] = item
        return items, order

    def recursive_move_line_items(
        self,
        items={},
        lines=[],
        page=0,
        limit=1000,
        order=None,
        typ="B"
    ):
        first_n=0
        last_n=limit
        model_code = self.genarate_pos_code(typ=typ, order=order, index=page)
        # if len(lines) > last_n:
        #     separate_lines = lines[first_n:last_n]
        #     del lines[first_n:last_n]
        #     items[page] = {
        #         'code': model_code,
        #         'company_id': order.company_id.id,
        #         'partner_id': order.partner_id.id,
        #         'invoice_date': date.today(),
        #         'line_ids': separate_lines
        #     }
        #     page += 1
        #     self.recursive_move_line_items(
        #         items=items, 
        #         lines=lines, 
        #         page=page, 
        #         limit=limit,
        #         order=order,
        #         typ=typ
        #     )
        # else:
        if len(lines):
            items[page] = {
                'code': model_code,
                'company_id': order.company_id.id,
                'partner_id': order.partner_id.id,
                'invoice_date': date.today(),
                'line_ids': lines
            }


    def create_summary_account_move_so_nhanh(self, line_items, order, limit):
        model = self.env['summary.account.move.so.nhanh']
        model_line = self.env['summary.account.move.so.nhanh.line']
        items = {}
        res = None
        if order:
            self.recursive_move_line_items(
                items=items,
                lines=list(line_items.values()),
                page=0,
                limit=limit,
                order=order,
                typ="B"
            )

            for k, v in items.items():
                res_line = model_line.create(v["line_ids"])
                v["line_ids"] = res_line.ids

            vals_list = list(items.values())

            res = model.create(vals_list)
        return res

    def create_summary_account_move_so_nhanh_return(self, line_items, order, limit):
        model = self.env['summary.account.move.so.nhanh.return']
        model_line = self.env['summary.account.move.so.nhanh.return.line']
        items = {}
        res = None
        if order:
            self.recursive_move_line_items(
                items=items,
                lines=list(line_items.values()),
                page=0,
                limit=limit,
                order=order,
                typ="T"
            )

            for k, v in items.items():
                res_line = model_line.create(v["line_ids"])
                v["line_ids"] = res_line.ids

            vals_list = list(items.values())

            res = model.create(vals_list)
        return res

    def handle_invoice_balance_clearing(
        self, 
        matching_records,
        v,
        sale_data,
        res,
        res_return
    ):
        summary_line_id = res.line_ids.filtered(
            lambda r: r.product_id.id == sale_data["product_id"]\
            and float(r.price_unit) == float(sale_data["price_unit"])
        )

        if not res_return:
            sale_data["return_line_id"] = None
        else:
            return_line_id = res_return.line_ids.filtered(
                lambda r: r.product_id.id == sale_data["product_id"]\
                and float(r.price_unit) == float(sale_data["price_unit"])
            )
            sale_data["return_line_id"] = return_line_id[0].id
        
            

        if v:
            sale_data["quantity"] -= v["quantity"]


        sale_data["remaining_quantity"] = sale_data["quantity"]
        sale_data["summary_line_id"] = summary_line_id[0].id


        matching_records.append(sale_data)


    def handle_invoice_difference(
        self, 
        remaining_records,
        synthetic_lines,
        v,
    ):
        is_adjusted = False
        if abs(v["quantity"]) > 0:
            if synthetic_lines:
                lines = synthetic_lines.filtered(
                    lambda r: r.line_pk == v["line_pk"]
                )
                if lines:
                    # line = lines[0]
                    # row = v

                    for line in lines:
                        row = v
                        if abs(line.remaining_quantity) >= abs(v["quantity"]):
                            row["quantity"] = -abs(row["quantity"])
                            row["price_unit"] = -abs(row["price_unit"])
                            row["price_unit_incl"] = -abs(row["price_unit_incl"])
                            row["synthetic_id"] = line.synthetic_id.id
                            
                            remaining_quantity = line.remaining_quantity - abs(v["quantity"])
                            adjusted_quantity = line.adjusted_quantity + abs(v["quantity"])

                            if remaining_records.get(line.synthetic_id.id):
                                remaining_records[line.synthetic_id.id].append(row)
                            else:
                                remaining_records[line.synthetic_id.id] = [row]
                            line.with_delay(
                                description="Adjusted invoice for POS and Nhanh.vn", channel="root.NhanhMQ"
                            ).write({
                                "remaining_quantity": remaining_quantity,
                                "adjusted_quantity": adjusted_quantity
                            })
                            break
                        else:
                            row["quantity"] = -abs(line.remaining_quantity)
                            v["quantity"] -= line.remaining_quantity
                            row["synthetic_id"] = line.synthetic_id.id
                            adjusted_quantity = line.adjusted_quantity + abs(line.remaining_quantity)

                            if remaining_records.get(line.synthetic_id.id):
                                remaining_records[line.synthetic_id.id].append(row)
                            else:
                                remaining_records[line.synthetic_id.id] = [row]

                            line.sudo().with_delay(
                                description="Adjusted invoice for POS", channel="root.NhanhMQ"
                            ).write({
                                "remaining_quantity": 0,
                                "adjusted_quantity": adjusted_quantity
                            })
                    is_adjusted = True
                # else:
                #     row = v
                #     row["quantity"] = abs(row["quantity"])

                #     if remaining_records.get('adjusted'):
                #         remaining_records['adjusted'].append(row)
                #     else:
                #         remaining_records['adjusted'] = [row]
            if not is_adjusted:
                row = v
                row["quantity"] = -abs(row["quantity"])
                row["price_unit"] = -abs(row["price_unit"])
                row["price_unit_incl"] = -abs(row["price_unit_incl"])
                row["synthetic_id"] = None
                if remaining_records.get('adjusted'):
                    remaining_records['adjusted'].append(row)
                else:
                    remaining_records['adjusted'] = [row]

    def recursive_balance_clearing_items(
        self,
        items={},
        lines=[],
        page=0,
        limit=1000,
        order=None
    ):
        first_n=0
        last_n=limit

        so_nhanh_license_bkav = self.env['ir.sequence'].next_by_code('so.nhanh.license.bkav')
        if len(lines) > last_n:
            separate_lines = lines[first_n:last_n]
            del lines[first_n:last_n]
            items[page] = {
                'code': so_nhanh_license_bkav,
                'company_id': order.company_id.id,
                'partner_id': order.partner_id.id,
                'invoice_date': date.today(),
                'line_ids': separate_lines
            }
            page += 1
            self.recursive_balance_clearing_items(
                items=items, 
                lines=lines, 
                page=page, 
                limit=limit,
                order=order
            )
        else:
            items[page] = {
                'code': so_nhanh_license_bkav,
                'company_id': order.company_id.id,
                'partner_id': order.partner_id.id,
                'invoice_date': date.today(),
                'line_ids': lines
            }

    def collect_invoice_balance_clearing(self, records, order, limit):
        items = {}
        model = self.env['synthetic.account.move.so.nhanh']
        model_line = self.env['synthetic.account.move.so.nhanh.line']
        if len(records):
            self.recursive_balance_clearing_items(
                items=items,
                lines=records,
                page=0,
                limit=limit,
                order=order
            )

            for k, v in items.items():
                res_line = model_line.create(v["line_ids"])
                v["line_ids"] = res_line.ids

            vals_list = list(items.values())

            res = model.create(vals_list)

    def collect_invoice_difference(self, records, order):
        model = self.env['summary.adjusted.invoice.so.nhanh']
        model_line = self.env['summary.adjusted.invoice.so.nhanh.line']
        vals_list = []
        i = 0
        if len(records.keys()):
            for k, v in records.items():
                res_line = model_line.create(v)
                so_nhanh_license_bkav = self.env['ir.sequence'].next_by_code('so.nhanh.license.bkav')
                vals_list.append({
                    'code': so_nhanh_license_bkav,
                    'company_id': order.company_id.id,
                    'partner_id': order.partner_id.id,
                    'invoice_date': date.today(),
                    'line_ids': res_line.ids,
                    'source_invoice': k if k != 'adjusted' else None,
                })
                i += 1
            res = model.create(vals_list)


    def get_sale_order_nhanh_not_exists_bkav(self, *args, **kwargs):
        move_date = datetime.utcnow().date()
        where_extra = ''
        params = ()

        if not kwargs.get("env"):
            where_extra = 'AND (am.invoice_date <= %s)'
            params = ((move_date,))

        query = """
            SELECT DISTINCT am.id 
            FROM sale_order so
            JOIN sale_order_line sol on sol.order_id = so.id
            JOIN sale_order_line_invoice_rel solir on solir.order_line_id = sol.id
            JOIN account_move_line aml on solir.invoice_line_id = aml.id
            JOIN account_move am on am.id = aml.move_id
            WHERE so.source_record = TRUE
            {where_extra}
            AND am.exists_bkav = 'f'
            AND am.state = 'posted'
            AND (am.is_general = 'f' OR am.is_general is NULL)
        """.format(where_extra=where_extra)
        self._cr.execute(query, params)
        result = self._cr.fetchall()
        move_ids = [idd[0] for idd in result]
        move_lines = self.env['account.move.line'].sudo().search([
            ('move_type', 'in', ['out_refund','out_invoice']),
            ('move_id', 'in', move_ids),
        ])
        move_out_refund_lines = move_lines.filtered(lambda r: r.move_type == 'out_refund')
        move_out_invoice_lines = move_lines.filtered(lambda r: r.move_type == 'out_invoice')

        return move_out_invoice_lines, move_out_refund_lines


    def get_last_synthetics(self):
        return self.env['synthetic.account.move.so.nhanh.line'].sudo().search([
            ('remaining_quantity', '>', 0),
            ('synthetic_id', '!=', False),
            ('exists_bkav', '=', True)
        ], order="invoice_date desc, id desc")


    def create_an_invoice_bkav(self):
        is_general_bkav_nhanh = self.env['ir.config_parameter'].sudo().get_param('bkav.is_general_bkav_nhanh')
        if is_general_bkav_nhanh:
            synthetic_account_move = self.with_context({"lang": "vi_VN"}).env['synthetic.account.move.so.nhanh'].search([('exists_bkav', '=', False)])
            synthetic_account_move.create_an_invoice()

            adjusted_move = self.with_context({"lang": "vi_VN"}).env['summary.adjusted.invoice.so.nhanh'].search([
                ('exists_bkav', '=', False),
                ('source_invoice', '!=', False)
            ])
            adjusted_move.create_an_invoice()


    def general_invoice_not_exists_bkav(self, *args, **kwargs):
        limit = 1000
        if kwargs.get("limit") and str(kwargs.get("limit")).isnumeric():
            limit = int(kwargs["limit"])

        synthetic_lines = self.get_last_synthetics()
        move_out_invoice_lines, move_out_refund_lines = self.get_sale_order_nhanh_not_exists_bkav(*args, **kwargs)

        move_out_invoice_items, order_out_invoice = self.include_line_by_product_and_price_bkav(move_out_invoice_lines)
        res = self.create_summary_account_move_so_nhanh(move_out_invoice_items, order_out_invoice, limit)

        move_out_refund_items, order_out_refund = self.include_line_by_product_and_price_bkav(move_out_refund_lines)
        res_refund = self.create_summary_account_move_so_nhanh_return(move_out_refund_items, order_out_refund, limit)
        matching_records = []
        remaining_records = {}
        
        if len(move_out_refund_items.keys()):
            for k, v in move_out_refund_items.items():
                if move_out_invoice_items.get(k):
                    sale_data = move_out_invoice_items.pop(k)
                    if abs(sale_data["quantity"]) > abs(v["quantity"]):
                        self.handle_invoice_balance_clearing(
                            matching_records,
                            v,
                            sale_data,
                            res,
                            res_refund
                        )
                    elif abs(sale_data["quantity"]) < abs(v["quantity"]):
                        v["quantity"] = abs(v["quantity"]) - abs(sale_data["quantity"])
                        self.handle_invoice_difference(
                            remaining_records,
                            synthetic_lines,
                            v
                        )
                else:
                    v["quantity"] = abs(v["quantity"])
                    self.handle_invoice_difference(
                        remaining_records,
                        synthetic_lines,
                        v
                    )

        if len(move_out_invoice_items.keys()):
            for k, v in move_out_invoice_items.items():
                self.handle_invoice_balance_clearing(
                    matching_records,
                    None,
                    v,
                    res,
                    None
                )
        order = order_out_invoice or order_out_refund
        self.collect_invoice_balance_clearing(matching_records, order, limit)
        self.collect_invoice_difference(remaining_records, order)


        if move_out_invoice_lines:
            move_ids = move_out_invoice_lines.mapped("move_id")
            move_ids.update({"is_general": True})
        

        if move_out_refund_lines:
            move_ids = move_out_refund_lines.mapped("move_id")
            move_ids.update({"is_general": True})


    def cronjob_collect_invoice_to_bkav_end_day(self, *args, **kwargs):
        self.general_invoice_not_exists_bkav(*args, **kwargs)
        self.create_an_invoice_bkav()


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


    def _check_info_before_bkav(self):
        return True

    @api.depends('data_compare_status')
    def _compute_data_compare_status(self):
        for rec in self:
            rec.invoice_state_e = dict(self._fields['data_compare_status'].selection).get(rec.data_compare_status)

    def get_invoice_identify(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_identify(self)

    def get_invoice_status(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_status(self)
    
    def create_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        data = self.get_bkav_data()
        origin_id = False
        is_publish = True
        issue_invoice_type = self.issue_invoice_type
        return bkav_action.create_invoice_bkav(self,data,is_publish,origin_id,issue_invoice_type)

    def publish_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.publish_invoice_bkav(self)

    def update_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        data = self.get_bkav_data()
        return bkav_action.create_invoice_bkav(self,data)

    def get_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.get_invoice_bkav(self)

    def cancel_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.cancel_invoice_bkav(self)

    def delete_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.delete_invoice_bkav(self)

    def download_invoice_bkav(self):
        if not self._check_info_before_bkav():
            return
        return bkav_action.download_invoice_bkav(self)

    def unlink(self):
        for item in self:
            item.delete_invoice_bkav()
        return super(GeneralInvoiceNotExistsBkav, self).unlink()


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
