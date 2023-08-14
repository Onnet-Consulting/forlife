# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ForlifeProduction(models.Model):
    _name = 'forlife.production'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Forlife Production"
    _rec_name = 'code'

    code = fields.Char("Production Order Code", required=True)
    name = fields.Char("Production Order Name", required=True)
    version = fields.Integer("Version", default=0, copy=False)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string="User Created", default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    created_date = fields.Date(string="Create Date", default=lambda self: fields.datetime.now(), required=True)
    forlife_production_finished_product_ids = fields.One2many('forlife.production.finished.product', 'forlife_production_id', string='Finished Products', copy=True)
    forlife_production_material_ids = fields.One2many('forlife.production.material', 'forlife_production_id', string='Materials')
    forlife_production_service_cost_ids = fields.One2many('forlife.production.service.cost', 'forlife_production_id', string='Service costs')
    implementation_id = fields.Many2one('account.analytic.account', string='Bộ phận thực hiện')
    management_id = fields.Many2one('account.analytic.account', string='Bộ phận quản lý')
    production_department = fields.Selection([
        ('tu_san_xuat', 'Hàng tự sản xuất'),
        ('tp', 'Gia công TP'),
        ('npl', 'Gia công NPL')
    ], default='tu_san_xuat', string='Production Department')
    produced_from_date = fields.Date(string="Produced From Date", default=lambda self: fields.datetime.now(), required=True)
    to_date = fields.Date(string="To Date", required=True)
    brand_id = fields.Many2one('res.brand', string="Nhãn hàng")
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('wait_confirm', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
    ], default='draft')
    status = fields.Selection([
        ('assigned', 'Chưa thực hiện'),
        ('in_approved', 'Đã nhập kho'),
        ('done', 'Hoàn thành'),
    ], compute='compute_check_status')
    check_status = fields.Boolean(default=False)
    machining_id = fields.Many2one('res.partner', string='Đối tượng gia công')
    leader_id = fields.Many2one('hr.employee', string='Quản lý đơn hàng')
    production_price = fields.Float(string='Đơn giá nhân công')

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})

    def action_wait_confirm(self):
        for record in self:
            record.write({'state': 'wait_confirm'})

    def action_approved(self):
        for record in self:
            old_record= self.env['forlife.production'].with_context(active_test=False).search([('id', '!=', record.id), ('code', '=', record.code)])
            record.write({
                'state': 'approved',
                'active': True,
                'version': len(old_record) + 1 if len(old_record) else 1
            })
            for old in old_record:
                old.write({'active': False})

    def action_done(self):
        for record in self:
            record.write({
                'check_status': True,
                'status': 'done'
            })

    @api.depends('forlife_production_finished_product_ids', 'forlife_production_finished_product_ids.remaining_qty', 'forlife_production_finished_product_ids.stock_qty')
    def compute_check_status(self):
        for rec in self:
            if not rec.check_status:
                if rec.forlife_production_finished_product_ids and any(x != 0 for x in rec.forlife_production_finished_product_ids.mapped('produce_qty')):
                    if all(x == 0 for x in rec.forlife_production_finished_product_ids.mapped('remaining_qty')):
                        rec.status = 'done'
                    elif all(x == 0 for x in rec.forlife_production_finished_product_ids.mapped('stock_qty')):
                        rec.status = 'assigned'

                    else:
                        rec.status = 'in_approved'

                else:
                    rec.status = 'assigned'
            else:
                rec.status = 'done'

    selected_product_ids = fields.Many2many('product.product', string='Selected Products', compute='compute_product_id')

    def action_open_history(self):
        return {
            'name': 'Version',
            'type': 'ir.actions.act_window',
            'res_model': 'forlife.production',
            'view_mode': 'tree,form',
            'domain': [('code', '=', self.code), ('active', '=', False)],
            'target': 'current',
        }

    @api.depends('forlife_production_finished_product_ids')
    def compute_product_id(self):
        for rec in self:
            if rec.forlife_production_finished_product_ids:
                self.selected_product_ids = [
                    (6, 0, [item.product_id.id for item in rec.forlife_production_finished_product_ids if item.product_id])]
            else:
                self.selected_product_ids = False

    @api.constrains('forlife_production_finished_product_ids')
    def constrains_forlife_production_finished_product_ids(self):
        for item in self:
            if not item.forlife_production_finished_product_ids:
                raise ValidationError("Bạn chưa nhập sản phẩm cho lệnh sản xuất!")

    @api.constrains('code')
    def constrains_code(self):
        for record in self:
            old_record = self.env['forlife.production'].search([('id', '!=', record.id), ('code', '=', record.code), ('active', '=', True), ('state', '=', 'approved')], limit=1)
            if old_record.status == 'done':
                raise ValidationError(_("Lệnh sản xuất đã tồn tại. Bạn nên tạo một lệnh sản xuất mới!"))

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu lệnh sản xuất'),
            'template': '/forlife_purchase/static/src/xlsx/template_lsx.xlsx?download=true'
        }]


class ForlifeProductionFinishedProduct(models.Model):
    _name = 'forlife.production.finished.product'
    _description = 'Forlife Production Finished Product'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'forlife_production_id'

    forlife_production_id = fields.Many2one('forlife.production', ondelete='cascade', string='Forlife Production')
    forlife_production_name = fields.Char(related='forlife_production_id.name', string='Forlife Production Name')
    product_id = fields.Many2one('product.product', required=True, string='Product')
    uom_id = fields.Many2one('uom.uom', string='Đơn vị lưu kho', related='product_id.uom_id')
    produce_qty = fields.Float(string='Produce Quantity', required=True)
    unit_price = fields.Float(readonly=1, string='Unit Price')
    stock_qty = fields.Float(string='Stock Quantity', compute='_compute_remaining_qty', store=1)
    remaining_qty = fields.Float(string='Remaining Quantity')
    description = fields.Char(string='Description', related='product_id.name')
    forlife_bom_ids = fields.Many2many('forlife.bom', string='Declare BOM')
    implementation_id = fields.Many2one('account.analytic.account', related='forlife_production_id.implementation_id')
    management_id = fields.Many2one('account.analytic.account', related='forlife_production_id.management_id')
    production_department = fields.Selection(related='forlife_production_id.production_department')
    forlife_bom_material_ids = fields.One2many('forlife.production.material', 'forlife_production_id', string='Materials')
    forlife_bom_service_cost_ids = fields.One2many('forlife.bom.service.cost', 'forlife_bom_id', string='Service costs')
    is_check = fields.Boolean(default=False)
    color = fields.Many2one('product.attribute.value', string='Màu', compute='compute_attribute_value')
    size = fields.Many2one('product.attribute.value', string='Size', compute='compute_attribute_value')
    quality = fields.Many2one('product.attribute.value', string='Chất lượng', compute='compute_attribute_value')

    @api.depends('product_id')
    def compute_attribute_value(self):
        for rec in self:
            rec.color = rec.product_id.attribute_line_ids.filtered(lambda x: x.attribute_id.attrs_code == 'AT004').value_ids.id
            rec.size = rec.product_id.attribute_line_ids.filtered(lambda x: x.attribute_id.attrs_code == 'AT006').value_ids.id
            rec.quality = rec.product_id.attribute_line_ids.filtered(lambda x: x.attribute_id.attrs_code == 'AT008').value_ids.id

    @api.constrains('produce_qty')
    def _constrains_produce_qty(self):
        for line in self:
            if line.produce_qty <= 0:
                raise ValidationError(_("Produce quantity must be greater than 0!"))

    @api.onchange('produce_qty', 'stock_qty')
    def onchange_remaining_qty(self):
        for rec in self:
            rec.remaining_qty = rec.produce_qty - rec.stock_qty

    def action_open_bom(self):
        return {
            'name': ('BOM'),
            'view_mode': 'form',
            'view_id': self.env.ref('forlife_purchase.forlife_production_finished_form').id,
            'res_model': 'forlife.production.finished.product',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }

    def update_price(self):
        for record in self:
            record.write({'write_date': fields.Datetime.now(),
                          'unit_price': sum(rec.total * rec.product_id.standard_price for rec in record.forlife_bom_material_ids)
                                        + sum(rec.rated_level for rec in record.forlife_bom_service_cost_ids)})
        return {
            'name': ('BOM'),
            'view_mode': 'form',
            'view_id': self.env.ref('forlife_purchase.forlife_production_finished_form').id,
            'res_model': 'forlife.production.finished.product',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('is_check'):
                vals.update({
                    'is_check': True
                })
        return super(ForlifeProductionFinishedProduct, self).create(vals_list)

    @api.constrains('produce_qty', 'stock_qty')
    def constrains_stock_qty_produce_qty(self):
        for rec in self:
            if rec.produce_qty < 0:
                raise ValidationError('Số lượng sản xuất không được âm!')
            elif rec.stock_qty < 0:
                raise ValidationError('Số lượng nhập kho không được âm!')
            elif rec.produce_qty < rec.stock_qty:
                raise ValidationError('Số lượng sản xuất phải lớn hơn số lượng nhập kho!!')

    # @api.constrains('forlife_bom_material_ids')
    # def constrains_forlife_bom_material_ids(self):
    #     for item in self:
    #         if not item.forlife_bom_material_ids:
    #             raise ValidationError("Bạn chưa nhập nguyên phụ liệu!")

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu bom'),
            'template': '/forlife_purchase/static/src/xlsx/template_bom.xlsx?download=true'
        }]


class ForlifeProductionMaterial(models.Model):
    _name = 'forlife.production.material'
    _description = 'Forlife Production Material'

    forlife_production_id = fields.Many2one('forlife.production.finished.product', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, string='Mã NPL')
    product_backup_id = fields.Many2one('product.product', string='Mã NPL thay thế')
    product_finish_id = fields.Many2one('product.product', string='Mã thành phẩm')
    description = fields.Char(string='Description', related="product_id.name")
    quantity = fields.Integer()
    uom_id = fields.Many2one(related="product_id.uom_id", string='Unit')
    production_uom_id = fields.Many2one('uom.uom', string='Production UoM')
    conversion_coefficient = fields.Float(string='Conversion Coefficient')
    rated_level = fields.Float(string='Rated level')
    loss = fields.Float(string='Loss %')
    total = fields.Float(string='Total', compute='compute_total')

    @api.depends('conversion_coefficient', 'rated_level', 'loss')
    def compute_total(self):
        for item in self:
            item.total = item.conversion_coefficient * item.rated_level * item.loss


class ForlifeProductionServiceCost(models.Model):
    _name = 'forlife.production.service.cost'
    _description = 'Forlife Production Service Cost'

    forlife_production_id = fields.Many2one('forlife.production', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    prices = fields.Monetary()


class ForlifeBOMServiceCost(models.Model):
    _name = 'forlife.bom.service.cost'
    _description = 'Forlife BOM Service Cost'

    forlife_bom_id = fields.Many2one('forlife.production.finished.product', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=1, string='Product')
    description = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    prices = fields.Monetary()
    rated_level = fields.Float(string='Rated level')

    @api.constrains('rated_level')
    def constrains_rated_level(self):
        for item in self:
            if item.rated_level < 0:
                raise ValidationError("Rated level must be greater than 0!")


class ForlifeBOMIngredients(models.Model):
    _name = 'forlife.bom.ingredients'
    _description = 'Forlife BOM Ingredients'

    forlife_bom_id = fields.Many2one('forlife.production.finished.product', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, string='Product')
    description = fields.Char(string='Description', related="product_id.name")
    uom_id = fields.Many2one(related="product_id.uom_id", string='Unit')
    production_uom_id = fields.Many2one('uom.uom', string='Production UoM')
    conversion_coefficient = fields.Float(string='Conversion Coefficient')
    rated_level = fields.Float(string='Rated level')
    loss = fields.Float(string='Loss %')
    total = fields.Float(string='Total')

    @api.constrains('conversion_coefficient')
    def constrains_conversion_coefficient(self):
        for item in self:
            if item.conversion_coefficient < 0:
                raise ValidationError("Conversion coefficient must be greater than 0!")

    @api.constrains('rated_level')
    def constrains_rated_level(self):
        for item in self:
            if item.rated_level < 0:
                raise ValidationError("Rated level must be greater than 0!")

    @api.constrains('loss')
    def constrains_loss(self):
        for item in self:
            if item.loss < 0:
                raise ValidationError("Loss must be greater than 0!")

    @api.constrains('total')
    def constrains_total(self):
        for item in self:
            if item.total < 0:
                raise ValidationError("Total must be greater than 0!")

    @api.constrains('conversion_coefficient')
    def constrains_conversion_coefficient(self):
        for item in self:
            if item.conversion_coefficient < 0:
                raise ValidationError("Conversion coefficient must be greater than 0!")

    @api.constrains('rated_level')
    def constrains_rated_level(self):
        for item in self:
            if item.rated_level < 0:
                raise ValidationError("Rated level must be greater than 0!")

    @api.constrains('loss')
    def constrains_loss(self):
        for item in self:
            if item.loss < 0:
                raise ValidationError("Loss must be greater than 0!")

    @api.constrains('total')
    def constrains_total(self):
        for item in self:
            if item.total < 0:
                raise ValidationError("Total must be greater than 0!")
