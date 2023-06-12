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
    user_id = fields.Many2one('res.users', string="User Created", default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    created_date = fields.Date(string="Create Date", default=lambda self: fields.datetime.now(), required=True)
    forlife_production_finished_product_ids = fields.One2many('forlife.production.finished.product',
                                                              'forlife_production_id', string='Finished Products')
    forlife_production_material_ids = fields.One2many('forlife.production.material', 'forlife_production_id',
                                                      string='Materials')
    forlife_production_service_cost_ids = fields.One2many('forlife.production.service.cost', 'forlife_production_id',
                                                          string='Service costs')
    implementation_department = fields.Selection([('di_nau', 'Xưởng Dị Nâu'),
                                                  ('minh_khai', 'Xưởng Minh Khai'),
                                                  ('nguyen_van_cu', 'Xưởng Nguyễn Văn Cừ'),
                                                  ('da_lat', 'Xưởng Đà Lạt'),
                                                  ('gia_cong', 'Gia công'),
                                                  ], default='di_nau', string='Implementation Department')
    management_department = fields.Selection([('tkl', 'Bộ phận sản xuất TKL'),
                                              ('fm', 'Bộ phận quản lý FM'),
                                              ('mua_hang', 'Phòng mua hàng')
                                              ], default='tkl', string='Management Department')
    production_department = fields.Selection([('tu_san_xuat', 'Hàng tự sản xuất'),
                                              ('tp', 'Gia công TP'),
                                              ('npl', 'Gia công NPL')
                                              ], default='tu_san_xuat', string='Production Department')
    produced_from_date = fields.Date(string="Produced From Date", default=lambda self: fields.datetime.now(), required=True)
    to_date = fields.Date(string="To Date", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('wait_confirm', 'Wait Confirm'),
        ('approved', 'Approved'),
    ], default='draft')
    status = fields.Selection([
        ('assigned', 'Assigned'),
        ('in_approved', 'In Approved'),
        ('done', 'Done'),
    ], default='assigned')

    quantity_order_line = fields.Many2many('quantity.production.order')
    quantity_lines = fields.One2many('quantity.production.order', 'production_id', string='')
    selected_product_ids = fields.Many2many('product.product', string='Selected Products', compute='compute_product_id')

    @api.depends('forlife_production_finished_product_ids')
    def compute_product_id(self):
        for rec in self:
            if rec.forlife_production_finished_product_ids:
                self.selected_product_ids = [
                    (6, 0, [item.product_id.id for item in rec.forlife_production_finished_product_ids if item.product_id])]
            else:
                self.selected_product_ids = False

    @api.constrains('code')
    def constrains_code(self):
        for rec in self:
            if rec.code and rec.search_count([('code', '=', rec.code)]) > 1:
                raise ValidationError(_('Production code already exists!'))

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
    uom_id = fields.Many2one('uom.uom', string='Unit', related='product_id.uom_id')
    produce_qty = fields.Float(string='Produce Quantity', required=True)
    unit_price = fields.Float(readonly=1, string='Unit Price')
    stock_qty = fields.Float(string='Stock Quantity')
    remaining_qty = fields.Float(string='Remaining Quantity')
    description = fields.Char(string='Description', related='product_id.name')
    forlife_bom_ids = fields.Many2many('forlife.bom', string='Declare BOM')
    implementation_department = fields.Selection(related='forlife_production_id.implementation_department')
    management_department = fields.Selection(related='forlife_production_id.management_department')
    production_department = fields.Selection(related='forlife_production_id.production_department')
    forlife_bom_material_ids = fields.One2many('forlife.production.material', 'forlife_production_id', string='Materials')
    forlife_bom_service_cost_ids = fields.One2many('forlife.bom.service.cost', 'forlife_bom_id', string='Service costs')
    forlife_bom_ingredients_ids = fields.One2many('forlife.bom.ingredients', 'forlife_bom_id', string='Ingredients')

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
                          'unit_price': sum(rec.total * rec.product_id.standard_price for rec in record.forlife_bom_material_ids) / record.produce_qty
                          + sum(rec.total * rec.product_id.standard_price for rec in record.forlife_bom_ingredients_ids) / record.produce_qty
                          + sum(rec.rated_level for rec in record.forlife_bom_service_cost_ids) / record.produce_qty})

    @api.onchange('forlife_bom_material_ids', 'forlife_bom_material_ids.total', 'forlife_bom_ingredients_ids', 'forlife_bom_ingredients_ids.total', 'forlife_bom_service_cost_ids', 'forlife_bom_service_cost_ids.rated_level')
    def _onchange_forlife_bom_material_ids(self):
        self.unit_price = (sum(rec.total * rec.product_id.standard_price for rec in self.forlife_bom_material_ids) / self.produce_qty
                          + sum(rec.total * rec.product_id.standard_price for rec in self.forlife_bom_ingredients_ids) / self.produce_qty
                          + sum(rec.rated_level for rec in self.forlife_bom_service_cost_ids) / self.produce_qty) if self.produce_qty else 0

    @api.constrains('produce_qty', 'stock_qty')
    def constrains_stock_qty_produce_qty(self):
        for rec in self:
            if rec.produce_qty < 0:
                raise ValidationError('Số lượng sản xuất không được âm!')
            elif rec.stock_qty < 0:
                raise ValidationError('Số lượng nhập kho không được âm!')
            elif rec.produce_qty < rec.stock_qty:
                raise ValidationError('Số lượng sản xuất phải lớn hơn số lượng nhập kho!!')

    @api.model
    def create(self, vals):
        current_order = self.env['forlife.production.finished.product'].search([('forlife_production_id', '=', vals['forlife_production_id']), ('product_id', '=', vals['product_id'])])
        current_order.unlink()
        line = super(ForlifeProductionFinishedProduct, self).create(vals)
        return line

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu bom'),
            'template': '/forlife_purchase/static/src/xlsx/Template Bom.xlsx?download=true'
        }]


class ForlifeProductionMaterial(models.Model):
    _name = 'forlife.production.material'
    _description = 'Forlife Production Material'

    forlife_production_id = fields.Many2one('forlife.production.finished.product', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, string='Product')
    description = fields.Char(string='Description', related="product_id.name")
    quantity = fields.Integer()
    uom_id = fields.Many2one(related="product_id.uom_id", string='Unit')
    production_uom_id = fields.Many2one('uom.uom', string='Production UoM')
    conversion_coefficient = fields.Float(string='Conversion Coefficient')
    rated_level = fields.Float(string='Rated level')
    loss = fields.Float(string='Loss %')
    total = fields.Float(string='Total')


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
