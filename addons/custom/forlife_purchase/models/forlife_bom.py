from odoo import api, fields, models


class ForlifeBOM(models.Model):
    _name = 'forlife.bom'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife BOM'

    code = fields.Char()
    name = fields.Char()
    quantity = fields.Integer()
    # can them truong don vi luu kho
    forlife_bom_material_ids = fields.One2many('forlife.bom.material', 'forlife_bom_id', string='Materials')
    forlife_bom_service_cost_ids = fields.One2many('forlife.bom.service.cost', 'forlife_bom_id', string='Service costs')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft')


class ForlifeBOMMaterial(models.Model):
    _name = 'forlife.bom.material'
    _description = 'Forlife BOM Material'

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    quantity = fields.Integer()
    uom_id = fields.Many2one('uom.uom', string='Uom Whs')


class ForlifeBOMServiceCost(models.Model):
    _name = 'forlife.bom.service.cost'
    _description = 'Forlife BOM Service Cost'

    forlife_bom_id = fields.Many2one('forlife.bom', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    prices = fields.Monetary()
