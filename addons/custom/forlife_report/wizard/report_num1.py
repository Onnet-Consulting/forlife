# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.forlife_report.wizard.report_base import format_date_query

PICKING_TYPE = [
    ('all', 'Tất cả'),
    ('retail', 'Bán lẻ'),
    ('wholesale', 'Bán buôn'),
    ('ecom', 'Bán Online')
]

TITLES = [
    'STT',
    'Kho',
    'Mã SP',
    'Tên SP',
    'Size',
    'Màu',
    'Đơn vị',
    'Giá',
    'Số lượng',
    'Chiết khấu',
    'Thành tiền',
    'Nhóm hàng',
    'Dòng hàng',
    'Kết cấu',
    'Mã loại SP',
    'Kênh bán',
]

COLUMN_WIDTHS = [5, 20, 20, 30, 15, 15, 10, 20, 8, 20, 25, 20, 20, 20, 20, 20]


class ReportNum1(models.TransientModel):
    _name = 'report.num1'
    _inherit = 'report.base'
    _description = 'Report revenue by product'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    picking_type = fields.Selection(PICKING_TYPE, 'Picking type', required=True, default='all')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def view_report(self):
        self.ensure_one()
        action = self.env.ref('forlife_report.report_num_1_client_action').read()[0]
        return action

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset

        query = f"""
                select row_number() over (order by pt.name)                                   as num,
                    wh.code                                                                   as warehouse,
                    pol.product_id                                                            as product_id,
                    pp.barcode                                                                as product_barcode,
                    coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name,
                    ''                                                                        as product_size,
                    ''                                                                        as product_color,
                    coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US') as uom_name,
                    pol.price_unit                                                            as price_unit,
                    pol.qty                                                                   as qty,
                    (pol.price_unit * pol.qty) * pol.discount / 100.0                         as discount,
                    pol.price_subtotal_incl                                                   as amount_with_tax,
                    split_part(cate.complete_name, ' / ', 2)                                  as product_group,
                    split_part(cate.complete_name, ' / ', 3)                                  as product_line,
                    split_part(cate.complete_name, ' / ', 4)                                  as texture_name,
                    aa.code                                                                   as product_type_code,
                    ''                                                                        as sale_channel
                from pos_order_line pol
                    left join product_product pp on pol.product_id = pp.id
                    left join product_template pt on pp.product_tmpl_id = pt.id
                    left join uom_uom uom on pt.uom_id = uom.id
                    left join pos_order po on pol.order_id = po.id
                    left join pos_session ps on ps.id = po.session_id
                    left join pos_config pc on ps.config_id = pc.id
                    left join store on store.id = pc.store_id
                    left join stock_warehouse wh on wh.id = store.warehouse_id
                    left join product_category cate on cate.id = pt.categ_id
                    left join ir_property ir on ir.res_id = concat('product.category,', pt.categ_id)
                    left join account_account aa on concat('account.account,',aa.id) = ir.value_reference
                where po.company_id = {self.company_id.id}
                    and ir.name='property_stock_valuation_account_id'
                    and ir.company_id = {self.company_id.id}
                    and po.state in ('paid', 'done', 'invoiced')
                    and {format_date_query("po.date_order", tz_offset)} >= '{self.from_date}'
                    and {format_date_query("po.date_order", tz_offset)} <= '{self.to_date}'
                """
        return query

    def get_data(self):
        self.ensure_one()
        query = self._get_query()
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        return {
            'titles': TITLES,
            'data': data,
        }

    def generate_xlsx_report(self, workbook):
        data = self.get_data()
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet(self._description)
        sheet.set_row(0, 25)
        sheet.write(0, 0, self._description, formats.get('header_format'))
        sheet.write(2, 0, _('From date: %s') % self.from_date.strftime('%d/%m/%Y'), formats.get('normal_format'))
        sheet.write(3, 0, _('To date: %s') % self.to_date.strftime('%d/%m/%Y'), formats.get('normal_format'))
        sheet.write(4, 0, _('Picking type: %s') % next((t[1] for t in self._fields.get('picking_type').selection if t[0] == self.picking_type), ''), formats.get('normal_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(6, idx, title, formats.get('title_format'))
            sheet.set_column(idx, idx, COLUMN_WIDTHS[idx])
        row = 7
        for value in data.get('data'):
            sheet.write(row, 0, value.get('num'), formats.get('center_format'))
            sheet.write(row, 1, value.get('warehouse'), formats.get('normal_format'))
            sheet.write(row, 2, value.get('product_barcode'), formats.get('normal_format'))
            sheet.write(row, 3, value.get('product_name'), formats.get('normal_format'))
            sheet.write(row, 4, value.get('product_size'), formats.get('normal_format'))
            sheet.write(row, 5, value.get('product_color'), formats.get('normal_format'))
            sheet.write(row, 6, value.get('uom_name'), formats.get('normal_format'))
            sheet.write(row, 7, value.get('price_unit'), formats.get('float_number_format'))
            sheet.write(row, 8, value.get('qty'), formats.get('center_format'))
            sheet.write(row, 9, value.get('discount'), formats.get('float_number_format'))
            sheet.write(row, 10, value.get('amount_with_tax'), formats.get('float_number_format'))
            sheet.write(row, 11, value.get('product_group'), formats.get('normal_format'))
            sheet.write(row, 12, value.get('product_line'), formats.get('normal_format'))
            sheet.write(row, 13, value.get('texture_name'), formats.get('normal_format'))
            sheet.write(row, 14, value.get('product_type_code'), formats.get('normal_format'))
            sheet.write(row, 15, value.get('sale_channel'), formats.get('normal_format'))
            row += 1
