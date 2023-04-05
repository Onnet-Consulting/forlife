from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ForlifeBOM(models.Model):
    _name = 'forlife.bom'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife BOM'
    _rec_name = 'forlife_production_id'

    code = fields.Char()
    name = fields.Char()

    forlife_production_id = fields.Many2one('forlife.production', required=1)
    forlife_production_name = fields.Char(related="forlife_production_id.name", required=1)
    product_id = fields.Many2one('product.product', required=1)
    description = fields.Char(string='Description', related="product_id.name", required=1)
    quantity = fields.Integer(string="Quantity", required=1)
    uom_id = fields.Many2one(related="product_id.uom_id")
    unit_prices = fields.Float(string="Unit Prices")
    prices_total = fields.Float(string="Prices Total")

    # can them truong don vi luu kho
    forlife_bom_material_ids = fields.One2many('forlife.bom.material', 'forlife_bom_id', string='Materials')
    forlife_bom_ingredients_ids = fields.One2many('forlife.bom.ingredients', 'forlife_bom_id', string='Ingredients')
    forlife_bom_service_cost_ids = fields.One2many('forlife.bom.service.cost', 'forlife_bom_id', string='Service costs')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft')

    implementation_department = fields.Selection([('di_nau', 'Xưởng Dị Nâu'),
                                                  ('minh_khai', 'Xưởng Minh Khai'),
                                                  ('nguyen_van_cu', 'Xưởng Nguyễn Văn Cừ'),
                                                  ('da_lat', 'Xưởng Đà Lạt'),
                                                  ('gia_cong', 'Gia công')], string='Implementation Department')
    management_department = fields.Selection([('tkl', 'Bộ phận sản xuất TKL'),
                                              ('fm', 'Bộ phận quản lý FM'),
                                              ('mua_hang', 'Phòng mua hàng')], string='Management Department')
    production_department = fields.Selection([('tu_san_xuat', 'Hàng tự sản xuất'),
                                              ('tp', 'Gia công TP'),
                                              ('npl', 'Gia công NPL')], string='Production Department')

    def update_price(self):
        current_bom = self.env['forlife.production.finished.product'].search(
            [('forlife_production_id', '=', self.forlife_production_id.id), ('product_id', '=', self.product_id.id)], limit=1)
        for record in self:
            record.write({'write_date': fields.Datetime.now(),
                          'unit_prices': sum(rec.total * rec.product_id.standard_price for rec in record.forlife_bom_material_ids) / record.quantity
                                         + sum(rec.total * rec.product_id.standard_price for rec in record.forlife_bom_ingredients_ids) / record.quantity
                                         + sum(rec.rated_level for rec in record.forlife_bom_service_cost_ids) / record.quantity})
            current_bom.write({'unit_price': record.unit_prices})

    @api.onchange('forlife_bom_material_ids', 'forlife_bom_material_ids.total')
    def _onchange_forlife_bom_material_ids(self):
        self.unit_prices = sum(rec.total * rec.product_id.standard_price for rec in self.forlife_bom_material_ids) / self.quantity if self.quantity else 0

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu bom'),
            'template': '/forlife_purchase/static/src/xlsx/template_bom.xlsx?download=true'
        }]


class ForlifeBOMMaterial(models.Model):
    _name = 'forlife.bom.material'
    _description = 'Forlife BOM Material'

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    description = fields.Char(string='Description', related="product_id.name")
    quantity = fields.Integer()
    uom_id = fields.Many2one(related="product_id.uom_id")
    production_uom_id = fields.Many2one('uom.uom', string='Production UoM')
    conversion_coefficient = fields.Float(string='Conversion Coefficient')
    rated_level = fields.Float(string='Rated level')
    loss = fields.Float(string='Loss %')
    total = fields.Float(string='Total')

    @api.constrains('conversion_coefficient', 'rated_level', 'loss', 'total')
    def constrains_conversion_coefficient_rated_level_loss_total(self):
        for item in self:
            if item.conversion_coefficient < 0:
                raise ValidationError(_("Conversion coefficient must be greater than 0!"))
            if item.rated_level < 0:
                raise ValidationError(_("Rated level must be greater than 0!"))
            if item.loss < 0:
                raise ValidationError(_("Loss must be greater than 0!"))
            if item.total < 0:
                raise ValidationError(_("Total must be greater than 0!"))

class ForlifeBOMServiceCost(models.Model):
    _name = 'forlife.bom.service.cost'
    _description = 'Forlife BOM Service Cost'

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=1)
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

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    description = fields.Char(string='Description', related="product_id.name")
    uom_id = fields.Many2one(related="product_id.uom_id")
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