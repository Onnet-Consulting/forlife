from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ProductDefective(models.Model):
    _name = 'product.defective'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = 'create_date desc'
    _description = 'Product Defective'
    _rec_name = 'product_id'

    store_id = fields.Many2one('store', 'Cửa hàng')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    quantity_defective_approved = fields.Integer('Số lượng lỗi đã duyệt')
    quantity_inventory_store = fields.Integer('Số lượng tồn theo cửa hàng', readonly=True, store=True, compute='compute_quantity_inventory_store')
    quantity_can_be_sale = fields.Integer('Số lượng lỗi có thể bán', tracking=True)
    price = fields.Float('Nguyên giá', related='product_id.lst_price')
    money_reduce = fields.Monetary('Số tiền giảm')
    percent_reduce = fields.Float('Phần trăm giảm (%)')
    total_reduce = fields.Monetary('Tổng giảm', compute='_compute_total_reduce', store=True)
    defective_type_id = fields.Many2one(
        'defective.type', 'Loại lỗi')
    detail_defective = fields.Char('Chi tiết lỗi')
    state = fields.Selection([
        ('new', 'New'),
        ('waiting approve', 'Waiting Approve'),
        ('approved','Approved'),
        ('refuse','Refuse'),
        ('cancel','Cancel')
    ], string='Trạng thái', default='new', tracking=True)
    is_already_in_use = fields.Boolean(default=False)
    program_pricelist_item_id = fields.Many2one('promotion.pricelist.item', "Giá (CT giá)")
    from_date = fields.Datetime(readonly=True, string='Hiệu lực', related='program_pricelist_item_id.program_id.campaign_id.from_date')
    to_date = fields.Datetime(readonly=True, related='program_pricelist_item_id.program_id.campaign_id.to_date')
    reason_refuse_product = fields.Char('Lí do từ chối', readonly=True)
    # active = fields.Boolean(default=True)
    quantity_require = fields.Integer('Số lượng yêu cầu')
    company_id = fields.Many2one('res.company', string='Công ty', required=True, default=lambda self: self.env.company)
    approval_uid = fields.Many2one('res.users', 'Người duyệt', readonly=True)
    approval_date = fields.Datetime('Ngày duyệt', readonly=True)
    department_id = fields.Many2one('hr.department', 'Bộ phận', related='pack_id.department_id')
    pack_id = fields.Many2one('product.defective.pack', 'Defective Pack', ondelete='cascade')
    selected = fields.Boolean('Selected', default=False, copy=False)
    is_transferred = fields.Boolean()
    transfer_state = fields.Selection([
        ('none', 'None'),
        ('to_transfer', 'To Transfer'),
        ('in_transfer', 'In Transfer')
    ], string='Transfer State', compute='_compute_transfer_state')
    transfer_line_ids = fields.One2many(
        'stock.transfer.line', 'defective_product_id')  # compute='_compute_transfer_line_ids')
    from_location_id = fields.Many2one(
        'stock.location', string='From Location', copy=False)
    to_location_id = fields.Many2one('stock.location', string='To Location', copy=False)
    image_1920 = fields.Image("Ảnh",  max_width=1920, max_height=1920)

    @api.constrains('defective_type_id', 'pack_id')
    def constrain_defective_type_id(self):
        for record in self:
            if len(record.pack_id.line_ids.mapped('defective_type_id.department_id.id')) > 1:
                raise ValidationError(
                    'Không được chọn loại lỗi thuộc bộ phận khác bộ phận đã khai báo trên cùng phiếu tổng hợp !')

    @api.depends('transfer_line_ids', 'is_transferred')
    def _compute_transfer_state(self):
        for record in self:
            record.transfer_state = 'none'
            if record.is_transferred and not record.transfer_line_ids:
                record.transfer_state = 'to_transfer'
            elif record.transfer_line_ids:
                record.transfer_state = 'in_transfer'

    @api.onchange('product_id')
    def change_product(self):
        if self.product_id and self.store_id:
            programs = self.env['promotion.program'].search([
                ('promotion_type', '=', 'pricelist'),
                ('state', '=', 'in_progress'),
                ('store_ids', 'in', self.store_id.id)
            ])
            program_pricelist_item_id = self.env['promotion.pricelist.item'].search([
                ('product_id', '=', self.product_id.id),
                ('program_id', 'in', programs.ids),
            ], limit=1, order="create_date DESC")
            self.with_context(show_price=True).program_pricelist_item_id = program_pricelist_item_id.id

    def unlink(self):
        for rec in self:
            if rec.is_already_in_use:
                raise ValidationError(_(f"KHông thể hoàn thành thao tác, có hàng lỗi đã được thực hiện bán!"))
            if rec.state != 'new':
                raise ValidationError(_(f"Bạn chỉ có thể xóa yêu cầu ở trạng thái Mới"))
        return super(ProductDefective, self).unlink()

    @api.depends('price', 'percent_reduce', 'money_reduce')
    def _compute_total_reduce(self):
        for rec in self:
            rec.total_reduce = (rec.price * rec.percent_reduce)/100 + rec.money_reduce

    def name_get(self):
        return [(rec.id, '%s' % rec.product_id.name) for rec in self]

    @api.depends('product_id', 'store_id')
    def compute_quantity_inventory_store(self):
        Quant = self.env['stock.quant']
        for rec in self:
            if rec.product_id and rec.store_id:
                available_quantity = Quant._get_available_quantity(product_id=rec.product_id, location_id=rec.store_id.warehouse_id.lot_stock_id, lot_id=None, package_id=None,
                                                                   owner_id=None, strict=False, allow_negative=False)
                if available_quantity:
                    rec.quantity_inventory_store = available_quantity
                else:
                    rec.quantity_inventory_store = 0
            else:
                rec.quantity_inventory_store = 0

    @api.onchange('money_reduce','percent_reduce')
    def onchange_price_defective(self):
        if self.money_reduce<0 or self.percent_reduce <0:
            raise UserError(_('Không được phép nhập số âm!'))
        if self.percent_reduce > 100:
            raise UserError(_('% giảm phải nhỏ hơn 100%!'))
        if self.money_reduce > 0 and self.percent_reduce > 0:
            raise UserError(_('Chỉ được phép nhập 1 trong 2 loại giảm!'))

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductDefective, self).create(vals_list)
        return res

    def action_send_request_approves(self):
        except_records = []
        for request in self.filtered(lambda r: r.state == 'new'):
            try:
                request.action_send_request_approve()
            except (ValidationError, UserError) as e:
                except_records.append((request, e))
        if except_records:
            message = (_('Lỗi xảy ra khi gửi yêu cầu duyệt: \n')
                       + '\n'.join([('- ' + str(e)) for rec, e in except_records]))
            action = self.env['ir.actions.actions']._for_xml_id('forlife_pos_product_change_refund.action_warning_popup')
            action['context'] = {
                'default_message': message
            }
            return action

    def action_send_request_approve(self):
        if any(line.quantity_require == 0 for line in self):
            raise UserError(_('Vui lòng nhập giá trị lớn hơn 0 cho Số lượng yêu cầu !'))

        product_defective_exits = self.env['product.defective'].sudo().search([('product_id','=',self.product_id.id), ('id','!=',self.id),('store_id','=',self.store_id.id),('state','=','approved')])
        if self.quantity_require > self.quantity_inventory_store - sum(product_defective_exits.mapped('quantity_can_be_sale')):
            raise ValidationError(_(f'Tồn kho của sản phẩm {self.product_id.name_get()[0][1]} không đủ trong kho {self.store_id.warehouse_id.name_get()[0][1]}'))
        self.state = 'waiting approve'
        if self.env.context.get('active_model', '') != 'product.defective.pack':
            self._send_mail_approve(self.id)

    def action_approves(self):
        except_records = []
        for request in self:
            try:
                request.action_approve()
            except (ValidationError, UserError) as e:
                except_records.append((request, e))
        if except_records:
            message = (_('Lỗi xảy ra khi duyệt: \n')
                       + '\n'.join([(f'- {rec.display_name}: ' + str(e)) for rec, e in except_records]))
            action = self.env['ir.actions.actions']._for_xml_id('forlife_pos_product_change_refund.action_warning_popup')
            action['context'] = {
                'default_message': message
            }
            return action

    def action_approve(self):
        self.ensure_one()
        if self.quantity_defective_approved <= 0.0:
            self.quantity_defective_approved = self.quantity_require
        product_defective_exits = self.env['product.defective'].sudo().search([('product_id', '=', self.product_id.id), ('id', '!=', self.id), ('store_id', '=', self.store_id.id), ('state', '=', 'approved')])
        if self.quantity_defective_approved > self.quantity_inventory_store - sum(product_defective_exits.mapped('quantity_can_be_sale')):
            raise ValidationError(_(f'Tồn kho của sản phẩm {self.product_id.name_get()[0][1]} không đủ trong kho {self.store_id.warehouse_id.name_get()[0][1]}'))
        self.quantity_can_be_sale = self.quantity_defective_approved
        if self.money_reduce == 0 and self.percent_reduce == 0:
            raise UserError(_('Vui lòng nhập giá trị lớn hơn 0 cho một trong hai trường "Số tiền giảm" và "Phần trăm giảm" !'))
        price = 0
        if self.program_pricelist_item_id:
            if self.total_reduce > self.program_pricelist_item_id.fixed_price:
                price = self.program_pricelist_item_id.fixed_price
        else:
            if self.total_reduce > self.price:
                price = self.price
        if price:
            raise UserError(_('Tổng giảm không được lớn hơn %s' % str(price)))

        self.write({
            'state': 'approved',
            'approval_uid': self._uid,
            'approval_date': fields.Datetime.now(),
        })

    def action_refuse(self):
        self.state = 'refuse'

    def action_cancel(self):
        self.write({
            'state': 'cancel',
            # 'active': False,
            'approval_uid': False,
            'approval_date': False,
        })

    def _send_mail_approve(self, id):
        mailTemplateModel = self.env['mail.template']
        irModelData = self.env['ir.model.data']
        templXmlId = irModelData._xmlid_to_res_id('forlife_pos_product_change_refund.email_template_handle_defective_product')
        baseUrl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirectUrl = baseUrl + '/web#id=%d&view_type=form&model=%s' % (id, self._name)
        if templXmlId:
            mailTmplObj = mailTemplateModel.browse(templXmlId)
            mailTmplObj.email_to = self.defective_type_id.email
            ctx = {
                'redirectUrl': redirectUrl,
            }
            mailTmplObj.with_context(**ctx).send_mail(id, force_send=True)

    @api.model
    def get_product_defective(self, store_id, products, store_name):
        if len(products) == 1:
            product_ids = str(tuple(products)).replace(',', '')
        else:
            product_ids = tuple(products)
        sql = f"SELECT pt.name as product_name, ppd.quantity_can_be_sale as quantity," \
              f"ppd.total_reduce as total_reduce,ppd.id as product_defective_id, ppd.detail_defective as detail_defective,ppd.product_id as product_id, dt.name as type_defective FROM product_defective ppd " \
              f"JOIN product_product pp on pp.id = ppd.product_id " \
              f"JOIN product_template pt on pt.id = pp.product_tmpl_id " \
              f"JOIN defective_type dt on dt.id = ppd.defective_type_id " \
              f"WHERE store_id = {store_id} AND product_id in {product_ids} AND quantity_can_be_sale >= 1 AND state = 'approved'"
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        for i in range(len(data)):
            data[i].update({
                'product_name': data[i]['product_name']['vi_VN'],
                'store_name': store_name,
                'id': i
            })
        return data

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu'),
            'template': '/forlife_pos_product_change_refund/static/src/xlsx/Mau_Xu_ly_hang_loi.xlsx?download=true'
        }]

    def copy_data(self, default=None):
        data_list = super().copy_data(default=default)
        for line, values in zip(self, data_list):
            values['money_reduce'] = 0
            values['percent_reduce'] = 0
            # values['active'] = True
            values['is_transferred'] = False
        return data_list

    def view_request(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("forlife_pos_product_change_refund.product_defective_action")
        form_view = [(self.env.ref('forlife_pos_product_change_refund.product_defective_form_view').id, 'form')]
        action['view_mode'] = 'form'
        action['res_id'] = self.id
        action['views'] = form_view
        action['domain'] = [('id', '=', self.id)]
        return action

    def view_image(self):
        # kanban_view = self.env.ref('forlife_pos_product_change_refund.product_defective_view_kanban_preview')
        form_view = self.env.ref('forlife_pos_product_change_refund.product_defective_view_form_preview')
        return {
            'name': _('Detailed Defective Products'),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban',
            'res_model': 'product.defective',
            'views': [(form_view.id, 'form')],
            'view_id': form_view.id,
            'target': 'new',
            'res_id': self.id,
            'domain': [('id', '=', self.id)],
        }
