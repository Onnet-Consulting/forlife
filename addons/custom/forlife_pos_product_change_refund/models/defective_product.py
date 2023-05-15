from odoo import api, fields, models


class ProductDefective(models.Model):
    _name = 'product.defective'
    _order = 'create_date desc'
    _description = 'Product Defective'

    store_id = fields.Many2one('store', 'Cửa hàng')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    product_id = fields.Many2one('product.template', 'Sản phẩm')
    quantity_defective_approved = fields.Integer('Số lượng lỗi đã duyệt')
    quantity_inventory_store = fields.Integer('Số lượng tồn theo cửa hàng', readonly=True, store=True)
    quantity_can_be_sale = fields.Integer('Số lượng lỗi có thể bán', readonly=True)
    price = fields.Monetary('Nguyên giá')
    money_reduce = fields.Monetary('Số tiền giảm')
    percent_reduce = fields.Monetary('Phần trăm giảm')
    total_reduce = fields.Monetary('Tổng giảm', compute='_compute_total_reduce', store=True)
    defective_type = fields.Many2one('defective.type', 'Loại lỗi')
    detail_defective = fields.Char('Chi tiết lỗi')
    state = fields.Selection([('new', 'New'), ('waiting approve', 'Waiting Approve'), ('approved','Approved'),('refuse','Refuse')], string='Trạng thái', default='new')

    @api.depends('price', 'percent_reduce', 'money_reduce')
    def _compute_total_reduce(self):
        for rec in self:
            rec.total_reduce = rec.price * rec.percent_reduce + rec.money_reduce

    def action_send_request_approve(self):
        self.state = 'waiting approve'
        self._send_mail_approve(self.id)

    def action_approve(self):
        self.state = 'approved'

    def action_refuse(self):
        self.state = 'refuse'

    def _send_mail_approve(self, id):
        mailTemplateModel = self.env['mail.template']
        irModelData = self.env['ir.model.data']
        templXmlId = irModelData._xmlid_to_res_id('forlife_pos_product_change_refund.email_template_handle_defective_product')
        baseUrl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirectUrl = baseUrl + '/web#id=%d&view_type=form&model=%s' % (id, self._name)
        if templXmlId:
            mailTmplObj = mailTemplateModel.browse(templXmlId)
            ctx = {
                'redirectUrl': redirectUrl,
            }
            mailTmplObj.with_context(**ctx).send_mail(id, force_send=True)

