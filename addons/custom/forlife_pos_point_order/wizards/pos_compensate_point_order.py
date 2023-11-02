# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo.osv import expression
import ast
import xlrd
import base64


class POSCompensatePoint(models.TransientModel):
    _name = 'pos.compensate.point.order'
    _description = "Compensate Point Wizard"

    order_ids = fields.Many2many(
        'pos.order', default=lambda self: self.env.context.get('active_ids'))
    reason = fields.Text(default='')

    # Dev: Thêm tính năng lọc để tích điểm bù cho 1 danh sách nhiều đơn hàng
    # Đầu vào: danh sách mã đơn từ file excel hoặc nhập tay, khoảng thời gian, khách hàng, thương hiệu
    import_file = fields.Binary(attachment=False, string='Tệp tham chiếu ĐH')
    import_file_name = fields.Char()
    po_domain = fields.Char(string='Bộ lọc', compute='_compute_po_domain')
    from_date = fields.Date('Từ ngày')
    to_date = fields.Date('Đến ngày')
    po_name = fields.Text("Tham chiếu đơn hàng")
    brand_id = fields.Many2one("res.brand", string="Thương hiệu")
    customer_ids = fields.Many2many('res.partner', string='Khách hàng', domain=lambda self: [('group_id', 'in', self.env['res.partner.group'].search([('code', '=', 'C')]).ids)])
    is_header = fields.Boolean('Có dòng tiêu đề', default=True)

    @api.depends('from_date', 'to_date', 'po_name', 'brand_id', 'customer_ids')
    def _compute_po_domain(self):
        default_dm = [('allow_compensate_point', '=', True)]
        for line in self:
            domain = []
            if line.brand_id:
                domain = expression.AND([domain, [('brand_id', '=', line.brand_id.id)]])
            if line.customer_ids:
                domain = expression.AND([domain, [('partner_id', 'in', line.customer_ids.ids)]])
            if line.po_name:
                po_name_list = line.po_name.split(',')
                domain = expression.AND([domain, [('name', 'in', [name.strip() for name in po_name_list])]])
            if line.from_date:
                from_date = datetime.combine(line.from_date, datetime.min.time()) + timedelta(hours=-7)
                domain = expression.AND([domain, [('date_order', '>=', from_date.strftime('%Y-%m-%d %H:%M:%S'))]])
            if line.to_date:
                to_date = datetime.combine(line.to_date, datetime.max.time()) + timedelta(hours=-7)
                domain = expression.AND([domain, [('date_order', '<=', to_date.strftime('%Y-%m-%d %H:%M:%S'))]])
            line.po_domain = str(expression.AND([domain, default_dm])) if domain else "[('id', '=', 0)]"

    def apply(self):
        self.order_ids.btn_compensate_points_all(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}

    def validate_order(self):
        self.ensure_one()
        domain = ast.literal_eval(self.po_domain)
        orders = self.env['pos.order'].search(domain)
        if not orders:
            raise ValidationError('Không tìm thấy đơn hàng để bù điểm, vui lòng kiểm tra lại bộ lọc !')
        return orders.with_context(active_ids=orders.ids).check_pos_order_compensate_point_from_list()

    def import_excel(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError(_("Bạn chưa tải lên file nhập !"))
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        sheet = workbook.sheet_by_index(0)
        po_names = []
        for row in range(sheet.nrows):
            if self.is_header and row == 0:
                continue
            po_names.append(sheet.cell(row, 0).value)
        self.update({
            'po_name': ','.join(po_names)
        })
        return self.return_self()

    def remove_all_customer_selected(self):
        self.customer_ids = [(5, 0, 0)]
        return self.return_self()

    def remove_all_po_name(self):
        self.update({
            'po_name': False,
            'import_file': False,
            'import_file_name': False
        })
        return self.return_self()

    def return_self(self):
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_pos_point_order.compensate_point_order_filter_action')
        action['res_id'] = self.id
        return action
