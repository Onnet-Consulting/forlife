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
    department_id = fields.Many2one('hr.department', 'Bộ phận')
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
        selected_lines.action_refuse()

    def action_approves(self):
        return self.line_ids.action_approves()

    def action_cancel(self):
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
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
