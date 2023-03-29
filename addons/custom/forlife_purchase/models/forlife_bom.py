from odoo import api, fields, models


class ForlifeBOM(models.Model):
    _name = 'forlife.bom'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife BOM'

    code = fields.Char()
    name = fields.Char()

    forlife_production_id = fields.Many2one('forlife.production')
    forlife_production_name = fields.Char(related="forlife_production_id.name")
    product_id = fields.Many2one('product.product')
    description = fields.Char(string='Description', related="product_id.name")
    quantity = fields.Integer(string="Quantity")
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

    def update_price(self):
        for record in self:
            record.write({'write_date': fields.Datetime.now()
                          })


class ForlifeBOMMaterial(models.Model):
    _name = 'forlife.bom.material'
    _description = 'Forlife BOM Material'

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char(string='Description', related="product_id.name")
    quantity = fields.Integer()
    uom_id = fields.Many2one(related="product_id.uom_id")
    production_uom_id = fields.Many2one('uom.uom', string='Production UoM')
    conversion_coefficient = fields.Float(string='Conversion Coefficient')
    rated_level = fields.Float(string='Rated level')
    loss = fields.Float(string='Loss %')
    total = fields.Float(string='Total')

class ForlifeBOMServiceCost(models.Model):
    _name = 'forlife.bom.service.cost'
    _description = 'Forlife BOM Service Cost'

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    prices = fields.Monetary()
    rated_level = fields.Float(string='Rated level')


class ForlifeBOMIngredients(models.Model):
    _name = 'forlife.bom.ingredients'
    _description = 'Forlife BOM Ingredients'

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char(string='Description', related="product_id.name")
    uom_id = fields.Many2one(related="product_id.uom_id")
    production_uom_id = fields.Many2one('uom.uom', string='Production UoM')
    conversion_coefficient = fields.Float(string='Conversion Coefficient')
    rated_level = fields.Float(string='Rated level')
    loss = fields.Float(string='Loss %')
    total = fields.Float(string='Total')
