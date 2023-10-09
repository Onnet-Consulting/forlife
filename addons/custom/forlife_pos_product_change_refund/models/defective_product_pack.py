import itertools
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ProductDefectivePack(models.Model):
    _name = 'product.defective.pack'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = 'create_date desc'
    _description = 'Product Defective Pack'
    _rec_name = 'store_id'
    _rec_names_search = ['name']

    name = fields.Char(string='Name', default=_('New'))
    brand_id = fields.Many2one('res.brand', string='Brand', store=True)
    store_id = fields.Many2one('store', 'Cửa hàng', required=True, domain="[('brand_id', '=', brand_id)]")
    user_id = fields.Many2one('res.users', 'Request User', default=lambda self: self.env.user.id)
    department_id = fields.Many2one('hr.department', 'Bộ phận', compute='_compute_department_id', store=False)
    note = fields.Text(tracking=True)
    line_ids = fields.One2many(
        'product.defective', 'pack_id', 'Defective Products', context={'active_test': False}, copy=True)
    state = fields.Selection([
        ('new', 'New'),
        ('waiting approve', 'Waiting Approve'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], string='Status', readonly=True, compute='_compute_state', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    show_transfer_state_col = fields.Boolean(compute='_show_transfer_state_col')
    transfer_ids = fields.One2many('stock.transfer', compute='_compute_transfers')
    transfer_count = fields.Integer(compute='_compute_transfers')
    show_create_transfer = fields.Boolean(compute='_show_create_transfer')

    @api.depends('line_ids')
    def _compute_transfers(self):
        for record in self:
            record.transfer_ids = record.line_ids.mapped('transfer_line_ids.stock_transfer_id')
            record.transfer_count = len(record.line_ids.mapped('transfer_line_ids.stock_transfer_id'))

    @api.depends('line_ids', 'line_ids.state')
    def _compute_state(self):
        for record in self:
            if all(line.state == 'new' for line in record.line_ids):
                record.state = 'new'
            elif all(line.state == 'cancel' for line in record.line_ids):
                record.state = 'cancel'
            elif all(line.state in ('cancel', 'approved', 'refuse') for line in record.line_ids):
                record.state = 'done'
            else:
                record.state = 'waiting approve'

    @api.depends('line_ids', 'line_ids.is_transferred')
    def _show_transfer_state_col(self):
        for record in self:
            record.show_transfer_state_col = any(line.is_transferred for line in record.line_ids)

    @api.depends('line_ids', 'line_ids.is_transferred')
    def _show_create_transfer(self):
        for record in self:
            record.show_create_transfer = any(line.is_transferred and not line.transfer_line_ids for line in record.line_ids)

    @api.depends('line_ids', 'line_ids.defective_type_id')
    def _compute_department_id(self):
        for record in self:
            record.department_id = record.line_ids and record.line_ids[0].defective_type_id.department_id or False

    def unlink(self):
        for rec in self:
            if rec.state != 'new' or any(line.state != 'new' for line in self.line_ids):
                raise ValidationError(_(f"Bạn chỉ có thể xóa yêu cầu ở trạng thái Mới"))
        return super(ProductDefectivePack, self).unlink()

    def action_send_requests(self):
        self._send_mail_approve(self.id)
        if not self.line_ids:
            raise UserError('Vui lòng thêm sản phẩm lỗi cần gửi duyệt!')
        return self.line_ids.with_context(active_model=self._name).action_send_request_approves()

    def _send_mail_approve(self, res_id):
        MailTemplate = self.env['mail.template']
        IrModelData = self.env['ir.model.data']
        templ_id = IrModelData._xmlid_to_res_id('forlife_pos_product_change_refund.email_template_handle_defective_product_pack')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_url = base_url + '/web#id=%d&view_type=form&model=%s' % (res_id, self._name)
        if templ_id:
            mailTmplObj = MailTemplate.browse(templ_id)
            mailTmplObj.email_to = ','.join(self.line_ids.mapped('defective_type_id.email'))
            ctx = {
                'redirectUrl': redirect_url
            }
            mailTmplObj.with_context(**ctx).send_mail(res_id, force_send=True)

    def action_refuse(self):
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            raise UserError('Không có dòng nào được chọn để Từ chối !')
        selected_lines.selected = False
        selected_lines.action_refuse()

    def action_approves(self):
        return self.line_ids.filtered(lambda l: l.state not in ('cancel', 'refuse')).action_approves()

    def action_cancel(self):
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            raise UserError('Không có dòng nào được chọn để Hủy !')
        selected_lines.selected = False
        selected_lines.action_cancel()

    def open_scan(self):
        view_id_form = self.env.ref('forlife_pos_product_change_refund.product_defective_scan_form_view')
        ctx = {'active_id': self.id}
        record = self.env['product.defective.scan'].create({
            'pack_id': self.id,

        })
        return {
            'name': _('Thêm sản phẩm lỗi'),
            'res_model': 'product.defective.scan',
            'type': 'ir.actions.act_window',
            'views': [(view_id_form.id, 'form')],
            'target': 'new',
            'res_id': record.id,
            'view_mode': 'form',
            'context': ctx,
        }

    def open_transfers(self):
        return {
            'name': _('Phiếu điều chuyển'),
            'res_model': 'stock.transfer',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.transfer_ids.ids)],
        }

    def action_create_transfer(self):
        to_transfer_lines = self.line_ids.filtered(
            lambda l: l.is_transferred and l.transfer_state == 'to_transfer'
        )
        location_grouped_lines = defaultdict(list)

        for line in to_transfer_lines:
            key = line.from_location_id, line.to_location_id
            location_grouped_lines[key].append(line)
        StockTransfer = self.env['stock.transfer'].sudo()
        transfers = self.env['stock.transfer']
        for key, grouped_lines in location_grouped_lines.items():
            company_id = self.store_id.company_id
            warehouse_id = self.store_id.warehouse_id
            location_id, location_dest_id = key
            line_data = []
            for line in grouped_lines:
                line_data.append((0, 0, {
                    'product_id': line.product_id.id,
                    'uom_id': line.uom_id.id,
                    'qty_plan': line.quantity_require,
                    'qty_out': line.quantity_require,
                    'qty_in': 0,
                    'stock_request_id': False,
                    'defective_product_id': line.id,
                }))

            transfers |= StockTransfer.create({
                'reference_document': self.name,
                'employee_id': self.env.user.employee_id.id or False,
                'department_id': self.department_id.id or False,
                'document_type': 'same_branch',
                'stock_request_id': False,
                'is_diff_transfer': False,
                'location_id': location_id.id,
                'location_name': location_id.display_name,
                'location_dest_id': location_dest_id.id,
                'location_dest_name': location_dest_id.display_name,
                'state': 'approved',
                'stock_transfer_line': line_data,
                'defective_product_ids': [(6, False, [line.id for line in grouped_lines])],
                'company_id': company_id.id
            })
        if transfers:
            transfers.action_out_approve()
