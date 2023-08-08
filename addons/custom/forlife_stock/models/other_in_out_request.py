from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ForlifeOtherInOutRequest(models.Model):
    _name = 'forlife.other.in.out.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife Other In Out Request'
    _order = 'create_date desc'

    def _domain_location_id(self):
        return "[('reason_type_id', '=', type_other_id)]"

    name = fields.code = fields.Char(string="Mã phiếu", default="New", copy=False)
    employee_id = fields.Many2one('hr.employee', string="Nhân viên")
    user_id = fields.Many2one('res.users', string="Người yêu cầu", required=True)
    department_id = fields.Many2one('hr.department', string="Phòng ban")
    company_id = fields.Many2one('res.company', string="Công ty", default=lambda self: self.env.company)
    type_other_id = fields.Many2one('forlife.reason.type', string='Loại lý do')
    type_other_code = fields.Char(related='type_other_id.code', string='Mã lý do')
    type_other = fields.Selection([
        ('other_import', 'Nhập khác'),
        ('other_export', 'Xuất khác'),], default='other_import', string='Loại phiếu', required=True)
    location_id = fields.Many2one('stock.location', string='Location From', domain=_domain_location_id)
    location_dest_id = fields.Many2one('stock.location', string='Location To')
    date_planned = fields.Datetime(string='Ngày kế hoạch', required=True)
    status = fields.Selection([
        ('draft', 'Dự thảo'),
        ('wait_approve', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy'),
        ('reject', 'Từ chối')], default='draft', copy=False)
    other_in_out_request_line_ids = fields.One2many('forlife.other.in.out.request.line', 'other_in_out_request_id', string='Chi tiết', copy=True)
    count_other_import_export = fields.Integer(compute="compute_count_other_import_export", copy=False)
    other_import_export_ids = fields.One2many('stock.picking', 'other_import_export_request_id', string="Other Import/Export")
    reject_reason = fields.Text()
    quantity_match = fields.Boolean(compute='compute_qty_match', store=1)
    is_last_transfer = fields.Boolean(string="Lần nhập kho cuối")

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['user_id'] = self.env.user.id if self.env.user else False
        res['department_id'] = self.env.user.department_default_id.id if self.env.user.department_default_id else False
        if "import_file" in self.env.context:
            if not self.env.user:
                raise ValidationError(_("Tài khoản chưa thiết lập nhân viên"))
            if not self.env.user.department_default_id:
                raise ValidationError(_("Tài khoản chưa thiết lập phòng ban"))
        return res

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id.department_default_id:
            self.department_id = self.user_id.department_default_id.id

    @api.onchange('type_other')
    def onchange_type_other(self):
        if self.type_other:
            self.type_other_id = False
            self.location_id = False
            self.location_dest_id = False

    @api.onchange('type_other_id')
    def _onchange_line_type_other_id(self):
        for rec in self.other_in_out_request_line_ids:
            rec.type_other_id = self.type_other_id.id

    @api.onchange('location_id')
    def _onchange_line_location_id(self):
        for rec in self.other_in_out_request_line_ids:
            rec.reason_to_id = self.location_id.id if self.type_other == 'other_import' else False
            rec.reason_from_id = self.location_id.id if self.type_other == 'other_export' else False

    @api.onchange('location_dest_id')
    def _onchange_line_location_dest_id(self):
        for rec in self.other_in_out_request_line_ids:
            rec.whs_to_id = self.location_dest_id.id if self.type_other == 'other_import' else False
            rec.whs_from_id = self.location_dest_id.id if self.type_other == 'other_export' else False

    @api.onchange('date_planned')
    def _onchange_line_date_planned(self):
        for rec in self.other_in_out_request_line_ids:
            rec.date_expected = self.date_planned

    @api.depends('other_import_export_ids', 'other_import_export_ids.state')
    def compute_qty_match(self):
        for rec in self:
            rec.quantity_match = all(x == 'done' for x in rec.other_import_export_ids.mapped('state')) \
                if rec.other_import_export_ids else False

    @api.constrains('other_in_out_request_line_ids')
    def _constrains_other_in_out_request_line_ids(self):
        for rec in self:
            if not rec.other_in_out_request_line_ids:
                raise ValidationError(_("Bạn chưa thêm sản phẩm nào"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('other.request.name.sequence') or 'YCNK'
        return super(ForlifeOtherInOutRequest, self).create(vals_list)

    def action_draft(self):
        for record in self:
            record.write({'status': 'draft'})

    def action_wait_approve(self):
        for record in self:
            if record.type_other_id.code == 'N01':
                line_productions = record.other_in_out_request_line_ids.filtered(lambda x: x.production_id)
                for rec in line_productions:
                    remaining_qty = rec.production_id.forlife_production_finished_product_ids.filtered(lambda r: r.product_id.id == rec.product_id.id).remaining_qty or 0
                    if rec.production_id and rec.quantity > remaining_qty:
                        raise ValidationError('Số lượng sản phẩm "%s" lớn hơn số lượng còn lại (%s) trong lệnh sản xuất %s!' % (rec.product_id.display_name, str(remaining_qty), rec.production_id.name))

            record.write({'status': 'wait_approve'})

    def action_approve(self):
        company_id = self.env.company.id
        picking_type_in = self.env['stock.picking.type'].search(
            [('company_id', '=', company_id), ('code', '=', 'incoming')], limit=1)
        picking_type_out = self.env['stock.picking.type'].search(
            [('company_id', '=', company_id), ('code', '=', 'outgoing')], limit=1)
        for record in self:
            for line in record.other_in_out_request_line_ids:
                if record.location_id.x_property_valuation_in_account_id != line.asset_id.asset_account:
                    raise ValidationError(
                    _('Tài khoản trong Mã tài sản của bạn khác với tài khoản trong cấu hình lý do nhập khác xuất khác!'))
            if record.type_other_id.code == 'N01':
                picking_type_in = self.env['stock.picking.type'].search([('company_id', '=', company_id), ('code', '=', 'incoming'), ('exchange_code', '=', 'incoming')], limit=1)
                if not picking_type_in:
                    raise ValidationError(_('Vui lòng cấu hình phương thức nhập kho thành phẩm cho công ty %s!', self.env.company.name))

            value = {}
            for item in record.other_in_out_request_line_ids:
                key = str(item.reason_to_id.id) + '_and_' + str(item.whs_to_id.id) if record.type_other == 'other_import' else (str(item.whs_from_id.id) + '_and_' + str(item.reason_from_id.id))
                data_other_line = (
                    0, 0, {
                        'product_id': item.product_id.id,
                        'ref_asset': item.asset_id,
                        'product_uom_qty': item.quantity,
                        'product_uom': item.uom_id.id,
                        'name': item.description,
                        'reason_type_id': item.type_other_id.id,
                        'reason_id': item.reason_to_id.id if record.type_other == 'other_import' else item.reason_from_id.id,
                        'is_amount_total': item.reason_to_id.is_price_unit,
                        'is_production_order': item.reason_to_id.is_work_order,
                        'location_id': item.reason_to_id.id if record.type_other == 'other_import' else item.whs_from_id.id,
                        'location_dest_id': item.whs_to_id.id if record.type_other == 'other_import' else item.reason_from_id.id,
                        'amount_total': item.product_id.standard_price if not item.reason_to_id.is_price_unit else 0,
                        'occasion_code_id': item.occasion_id.id,
                        'work_production': item.production_id.id,
                        'account_analytic_id': item.cost_center.id,
                        'product_other_id': item.id,
                        'picking_id': record.id
                    })
                dict_data = {
                    'state': 'draft',
                    'reason_type_id': item.type_other_id.id,
                    'other_import': True if record.type_other == 'other_import' else False,
                    'other_export': True if record.type_other == 'other_export' else False,
                    'location_id': item.reason_to_id.id if record.type_other == 'other_import' else item.whs_from_id.id,
                    'location_dest_id': item.whs_to_id.id if record.type_other == 'other_import' else item.reason_from_id.id,
                    'picking_type_id': picking_type_in.id if record.type_other == 'other_import' else picking_type_out.id,
                    'company_id': self.env.company.id,
                    'scheduled_date': record.date_planned,
                    'is_from_request': True,
                    'origin': record.name,
                    'other_import_export_request_id': record.id,
                    'is_last_transfer': record.is_last_transfer,
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

    @api.model
    def load(self, fields, data):
        if "import_file" in self.env.context:
            for record in data:
                if 'other_in_out_request_line_ids/product_id' in fields and not record[fields.index('other_in_out_request_line_ids/product_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường sản phẩm"))
                if 'other_in_out_request_line_ids/date_expected' in fields and not record[fields.index('other_in_out_request_line_ids/date_expected')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường ngày dự kiến"))
                if 'other_in_out_request_line_ids/quantity' in fields and not record[fields.index('other_in_out_request_line_ids/quantity')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường số lượng"))
                if 'other_in_out_request_line_ids/uom_id' in fields and not record[fields.index('other_in_out_request_line_ids/uom_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường đơn vị"))
                if 'other_in_out_request_line_ids/type_other_id' in fields and not record[fields.index('other_in_out_request_line_ids/type_other_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường loại lý do"))
                if 'other_in_out_request_line_ids/whs_from_id' in fields and not record[fields.index('other_in_out_request_line_ids/whs_from_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường từ kho"))
                if 'other_in_out_request_line_ids/whs_to_id' in fields and not record[fields.index('other_in_out_request_line_ids/whs_to_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường đến kho"))
                if 'other_in_out_request_line_ids/reason_from_id' in fields and not record[fields.index('other_in_out_request_line_ids/reason_from_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường lý do xuất"))
                if 'other_in_out_request_line_ids/reason_to_id' in fields and not record[fields.index('other_in_out_request_line_ids/reason_to_id')]:
                    raise ValidationError(_("Thiếu giá trị bắt buộc cho trường lý do nhập"))
        return super().load(fields, data)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu yêu cầu nhập khác'),
            'template': '/forlife_stock/static/src/xlsx/template_ycnk.xlsx?download=true'
        }, {
            'label': _('Tải xuống mẫu yêu cầu xuất khác'),
            'template': '/forlife_stock/static/src/xlsx/template_ycxk.xlsx?download=true'
        }]


class ForlifeOtherInOutRequestLine(models.Model):
    _name = 'forlife.other.in.out.request.line'
    _description = 'Forlife Other In Out Request Line'

    def _domain_location_id(self):
        return "[('reason_type_id', '=', type_other_id)]"
    other_in_out_request_id = fields.Many2one('forlife.other.in.out.request', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', required=True, string='Sản phẩm')
    description = fields.Char(string='Mô tả', related="product_id.name")
    asset_id = fields.Many2one('assets.assets', string='Tài sản')
    date_expected = fields.Datetime(string='Ngày dự kiến')
    type_other_id = fields.Many2one('forlife.reason.type', string='Loại lý do')
    quantity = fields.Float(string='Số lượng', required=True)
    uom_id = fields.Many2one('uom.uom', string='Đơn vị')
    whs_from_id = fields.Many2one('stock.location', string='Từ kho')
    reason_from_id = fields.Many2one('stock.location', string='Lý do xuất', domain=_domain_location_id)
    whs_to_id = fields.Many2one('stock.location', string='Đến kho')
    reason_to_id = fields.Many2one('stock.location', string='Lý do nhập', domain=_domain_location_id)
    occasion_id = fields.Many2one('occasion.code', string='Mã vụ việc')
    production_id = fields.Many2one('forlife.production', string='Lệnh sản xuất', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], ondelete='restrict')
    cost_center = fields.Many2one('account.analytic.account', string='Trung tâm chi  phí')
    stock_move_ids = fields.One2many('stock.move', 'product_other_id')

    @api.constrains('quantity')
    def _constrains_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("Số lượng phải lớn hơn 0"))

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('import_file'):
            for vals in vals_list:
                product = self.env['product.product'].browse(vals.get('product_id'))
                if product and vals.get('uom_id') and vals.get('uom_id') != product.uom_id.id:
                    raise ValidationError(_("Đơn vị nhập vào không khớp với đơn vị lưu kho của sản phẩm [%s] %s" % (product.code, product.name)))
        return super(ForlifeOtherInOutRequestLine, self).create(vals_list)


