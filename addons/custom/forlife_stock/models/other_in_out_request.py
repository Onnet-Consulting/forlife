from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ForlifeOtherInOutRequest(models.Model):
    _name = 'forlife.other.in.out.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife Other In Out Request'

    name = fields.code = fields.Char(string="Mã phiếu", default="New", copy=False)
    employee_id = fields.Many2one('hr.employee', string="Nhân viên", default=lambda self: self.env.user.employee_id.id)
    department_id = fields.Many2one('hr.department', string="Phòng ban", related='employee_id.department_id')
    company_id = fields.Many2one('res.partner', string="Công ty")
    type_other_id = fields.Many2one('forlife.reason.type', string='Loại lý do', required=True)
    type_other = fields.Selection([('other_import', 'Nhập khác'),
                                   ('other_export', 'Xuất khác'),
                                   ], default='other_import', string='Loại phiếu', required=True)
    location_id = fields.Many2one('stock.location', string='Location From', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Location To', required=True)
    date_planned = fields.Datetime(string='Ngày kế hoạch')
    status = fields.Selection([('draft', 'Dự thảo'),
                               ('wait_approve', 'Chờ duyệt'),
                               ('approved', 'Đã duyệt'),
                               ('done', 'Hoàn thành'),
                               ('cancel', 'Hủy'),
                               ('reject', 'Từ chối')], default='draft', copy=False)
    other_in_out_request_line_ids = fields.One2many('forlife.other.in.out.request.line', 'other_in_out_request_id', string='Stock Picking', copy=True)
    count_other_import_export = fields.Integer(compute="compute_count_other_import_export", copy=False)
    other_import_export_ids = fields.One2many('stock.picking', 'other_import_export_request_id',
                                              string="Other Import/Export")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('other.request.name.sequence') or 'YCNK'
        return super(ForlifeOtherInOutRequest, self).create(vals)

    def action_draft(self):
        for record in self:
            record.write({'status': 'draft'})

    def action_wait_approve(self):
        for record in self:
            record.write({'status': 'wait_approve'})

    def action_approve(self):
        for record in self:
            value = {}
            for item in record.other_in_out_request_line_ids:
                key = str(item.reason_to_id.id) + '_and_' + str(item.whs_to_id.id) if record.type_other == 'other_import' else (str(item.whs_from_id.id) + '_and_' + str(item.reason_from_id.id))
                data_other_line = (
                    0, 0, {'product_id': item.product_id.id,
                           'product_uom_qty': item.quantity,
                           'product_uom': item.uom_id.id,
                           'name': item.description,
                           'reason_type_id': record.type_other_id.id,
                           'reason_id': item.reason_to_id.id,
                           'is_amount_total': item.reason_to_id.is_price_unit,
                           'is_production_order': item.reason_to_id.is_work_order,
                           'location_id': record.location_id.id,
                           'location_dest_id': record.location_dest_id.id,
                           'amount_total': item.product_id.standard_price if not item.reason_to_id.is_price_unit else 0,
                           'occasion_code_id': item.occasion_id.id,
                           'work_production': item.production_id.id,
                           'account_analytic_id': item.cost_center.id,
                           'product_other_id': item.id,
                           'picking_id': record.id})
                dict_data = {'state': 'draft',
                             'reason_type_id': record.type_other_id.id,
                             'other_import': True,
                             'location_id': record.location_id.id,
                             'location_dest_id': record.location_dest_id.id,
                             'picking_type_id': self.env.ref('stock.picking_type_in').id if record.type_other == 'other_import' else self.env.ref('stock.picking_type_out').id,
                             'company_id': self.env.company.id,
                             'scheduled_date': record.date_planned,
                             'origin': record.name,
                             'other_import_export_request_id': record.id,
                             'move_ids_without_package': [data_other_line]
                             }
                if value.get(key):
                    value[key]['move_ids_without_package'].append(data_other_line)
                else:
                    value.update({
                        key: dict_data
                    })
            for item in value:
                data_other_import_export = self.env['stock.picking'].create(value.get(item))
            record.write({'status': 'approved'})
            context = {'other_import_export_request_id': self.id, 'create': False, 'delete': True, 'edit': True}
            return {
                'name': _('List Other Import/Export'),
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('other_import_export_request_id', '=', record.id)],
                'context': context
            }

    def action_done(self):
        for record in self:
            request = self.env['stock.picking'].search_count([('other_import_export_request_id', '=', record.id), ('state', '!=', 'done')])
            if request > 0:
                raise ValidationError(_("Bạn cần xử lý các phiếu nhập khác/xuất khác chưa hoàn thành trước!"))
            record.write({'status': 'done'})

    def action_cancel(self):
        for record in self:
            record.write({'status': 'cancel'})

    def action_other_import_export(self):
        context = {'other_import_export_request_id': self.id, 'create': True, 'delete': True, 'edit': True}
        return {
            'name': _('List Other Import/Export'),
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('other_import_export_request_id', '=', self.id)],
            'context': context
        }

    def compute_count_other_import_export(self):
        for item in self:
            item.count_other_import_export = len(item.other_import_export_ids)


class ForlifeOtherInOutRequestLine(models.Model):
    _name = 'forlife.other.in.out.request.line'
    _description = 'Forlife Other In Out Request Line'

    other_in_out_request_id = fields.Many2one('forlife.other.in.out.request', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', required=True, string='Sản phẩm')
    description = fields.Char(string='Mô tả', related="product_id.name")
    asset_id = fields.Many2one('assets.assets', string='Tài sản')
    date_expected = fields.Datetime(string='Ngày dự kiến')
    quantity = fields.Float(string='Số lượng')
    uom_id = fields.Many2one(related="product_id.uom_id", string='Đơn vị')
    whs_from_id = fields.Many2one('stock.location', string='Từ kho')
    reason_from_id = fields.Many2one('stock.location', string='Lý do')
    whs_to_id = fields.Many2one('stock.location', string='Đến kho')
    reason_to_id = fields.Many2one('stock.location', string='Lý do')
    occasion_id = fields.Many2one('occasion.code', string='Mã vụ việc')
    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất')
    cost_center = fields.Many2one('account.analytic.account', string='Trung tâm chi  phí')
    stock_move_ids = fields.One2many('stock.move', 'product_other_id')

