# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DDF, DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime, timedelta
import xlrd
import pytz
import ast


def convert_localize_datetime(value, tz):
    tz_name = tz or 'UTC'
    utc_datetime = pytz.utc.localize(value, is_dst=False)
    try:
        context_tz = pytz.timezone(tz_name)
        localized_datetime = utc_datetime.astimezone(context_tz)
    except Exception:
        localized_datetime = utc_datetime
    return localized_datetime


class ResUtility(models.AbstractModel):
    _name = 'res.utility'
    _description = 'Utility Methods'

    @api.model
    def read_xls_book(self, book, sheet_index):
        sheet = book.sheet_by_index(sheet_index)
        # emulate Sheet.get_rows for pre-0.9.4
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value)
                        if is_float
                        else str(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DDF)
                        if is_datetime
                        else dt.strftime(DF)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s") % {
                            'row': rowx,
                            'col': colx,
                            'cell_value': xlrd.error_text_from_code.get(cell.value,
                                                                        _("unknown error code %s") % cell.value)
                        }
                    )
                else:
                    values.append(cell.value)
            yield values

    def get_attribute_code_config(self):
        return ast.literal_eval(self.env.ref('forlife_base.attr_code_default').attr_code or '{}')

    @api.model
    def get_warehouse_type_info(self):
        return self.env['stock.warehouse.type'].search_read([], ['id', 'code', 'name'])

    @api.model
    def get_allowed_company(self):
        return [{
            'id': c.id,
            'name': c.name,
            'code': c.code,
        } for c in self.env.user.company_ids]

    @api.model
    def get_warehouse_info(self, wh_type_code, company_code):
        return self.env['stock.warehouse'].search_read([('whs_type.code', '=', wh_type_code), ('company_id.code', '=', company_code)], ['id', 'code', 'name'])

    @api.model
    def get_stock_inventory_by_wh_id(self, wh_id):
        data = self.env['stock.inventory'].search([('company_id', '=', self.env.user.company_id.id),
                                                   ('warehouse_id', '=', wh_id),
                                                   ('state', 'in', ('first_inv', 'second_inv'))])
        return [{
            'id_phieu_kk': inv.id,
            'so_phieu_kk': inv.name,
            'dia_diem': inv.mapped('location_ids.complete_name'),
            'trang_thai': 'kk_b1' if inv.state == 'first_inv' else 'kk_b2',
            'tong_ton': sum(inv.mapped('line_ids.theoretical_qty'))
        } for inv in data]

    @api.model
    def get_stock_inventory_detail(self, inv_id):
        data = self.env['stock.inventory'].search([('id', '=', inv_id)])
        return [{
            'barcode': line.product_id.barcode,
            'quantity': line.theoretical_qty
        } for line in data.mapped('line_ids')]

    @api.model
    def get_question_info(self, customer_phone, brand):
        question_id = self.env['forlife.comment'].search([("customer_code", "=", customer_phone), ("brand", "=", brand), ("status", "=", 0)], limit=1).question_id or 0
        question_data = self.env['forlife.question'].search_read(
            [('id', '=', question_id)],
            ["header", "question1", "sub_quest1", "sub_quest2", "question2", "success1", "success2", "success3", "banner_question", "banner_success", "icon", "rate"]
        )
        return question_data[0] if question_data else {}

    @api.model
    def update_net_promoter_score(self, customer_phone, brand, point, comment):
        comment_id = self.env['forlife.comment'].search([("customer_code", "=", customer_phone), ("brand", "=", brand), ("status", "=", 0)], limit=1)
        if comment_id:
            comment_id.with_context(update_comment=True).sudo().write({
                'point': point,
                'comment': comment,
                'status': 1,
                'comment_date': fields.Datetime.now(),
            })
            return {
                'id': comment_id.id,
                'phone': comment_id.customer_code,
                'point': comment_id.point,
                'comment': comment_id.comment,
            }
        return False

    @api.model
    def get_stock_quant_in_warehouse_by_barcode(self, wh_id, barcode):
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        wh = self.env['stock.warehouse'].search([('id', '=', wh_id)])
        if any([not product, not wh, not wh_id, not barcode]):
            return {}
        stock_move = self.env['stock.move'].search(['&', '&', '&', ('product_id', '=', product.id),
                                                    ('state', '=', 'done'), ('company_id', '=', wh.company_id.id),
                                                    '|', ('location_id.warehouse_id', '=', wh_id), ('location_dest_id.warehouse_id', '=', wh_id)])
        fix_price = self.env['promotion.pricelist.item'].search([('product_id', '=', product.id), ('program_id.active', '=', True),
                                                                 ('program_id.campaign_id.company_id', '=', wh.company_id.id),
                                                                 ('program_id.campaign_id.from_date', '<=', fields.Datetime.now()),
                                                                 ('program_id.campaign_id.to_date', '>', fields.Datetime.now()),
                                                                 ('program_id.campaign_id.state', '=', 'in_progress'),
                                                                 ]).sorted(lambda f: (f.program_id.campaign_id.from_date, -f.id))
        sale_price = fix_price[0].fixed_price or product.lst_price
        qty_out = sum(stock_move.filtered(lambda f: f.location_id.warehouse_id.id == wh_id).mapped('product_qty'))
        qty_in = sum(stock_move.filtered(lambda f: f.location_dest_id.warehouse_id.id == wh_id).mapped('product_qty'))
        attr_value = self.env['res.utility'].get_attribute_code_config()
        return {
            'barcode': product.barcode,
            'ten_san_pham': product.name,
            'so_luong': qty_in - qty_out,
            'mau_sac': ', '.join(product.attribute_line_ids.filtered(lambda f: f.attribute_id.attrs_code == attr_value.get('mau_sac', '')).mapped('value_ids.name')),
            'size': ', '.join(product.attribute_line_ids.filtered(lambda f: f.attribute_id.attrs_code == attr_value.get('size', '')).mapped('value_ids.name')),
            'gioi_tinh': ', '.join(product.attribute_line_ids.filtered(lambda f: f.attribute_id.attrs_code == attr_value.get('doi_tuong', '')).mapped('value_ids.name')),
            'gia_ban': sale_price,
        }

    @api.model
    def get_stock_warehouse_info_by_barcode(self, wh_type_code, barcode):
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        wh_type = self.env['stock.warehouse.type'].search([('code', '=', wh_type_code)])
        if any([not product, not wh_type, not wh_type_code, not barcode]):
            return []
        stock_move = self.env['stock.move'].search(['&', '&', ('product_id', '=', product.id), ('state', '=', 'done'),
                                                    '|', ('location_id.warehouse_id.whs_type', '=', wh_type.id),
                                                    ('location_dest_id.warehouse_id.whs_type', '=', wh_type.id)])
        wh_out_ids = stock_move.mapped('location_id.warehouse_id').filtered(lambda f: f.whs_type.id == wh_type.id)
        wh_in_ids = stock_move.mapped('location_dest_id.warehouse_id').filtered(lambda f: f.whs_type.id == wh_type.id)
        result = []
        for wh in set(wh_out_ids.ids + wh_in_ids.ids):
            sm_out = sum(stock_move.filtered(lambda x: x.location_id.warehouse_id.id == wh).mapped('product_qty'))
            sm_in = sum(stock_move.filtered(lambda x: x.location_dest_id.warehouse_id.id == wh).mapped('product_qty'))
            if sm_out < sm_in:
                _wh = wh_out_ids.filtered(lambda w: w.id == wh) or wh_in_ids.filtered(lambda w: w.id == wh)
                result.append({
                    'ma_kho': _wh.code,
                    'ten_kho': _wh.name,
                    'so_luong': sm_in - sm_out,
                })
        return result
