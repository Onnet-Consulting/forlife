# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ForlifeProduction(models.Model):
    _name = 'forlife.production'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Forlife Production"
    _rec_name = 'code'

    # name = fields.Char("Name")
    code = fields.Char("Production Order Code", required=1)
    name = fields.Char("Production Order Name", required=1)
    user_id = fields.Many2one('res.users', string="User Created", default=lambda self: self.env.user, required=1)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    create_date = fields.Date(string="Create Date", default=fields.Date.context_today, required=1)
    forlife_production_finished_product_ids = fields.One2many('forlife.production.finished.product',
                                                              'forlife_production_id', string='Finished Products')
    forlife_production_material_ids = fields.One2many('forlife.production.material', 'forlife_production_id',
                                                      string='Materials')
    forlife_production_service_cost_ids = fields.One2many('forlife.production.service.cost', 'forlife_production_id',
                                                          string='Service costs')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft')


class ForlifeProductionFinishedProduct(models.Model):
    _name = 'forlife.production.finished.product'
    _description = 'Forlife Production Finished Product'

    forlife_production_id = fields.Many2one('forlife.production', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=1)
    uom_id = fields.Many2one(string='Unit', related='product_id.uom_id')
    produce_qty = fields.Float(string='Produce Quantity', required=1)
    unit_price = fields.Float(string='Price')
    stock_qty = fields.Float(string='Stock Quantity', required=1)
    remaining_qty = fields.Float(string='Remaining Quantity', compute='_compute_remaining_qty')
    description = fields.Char(String='Description')
    forlife_bom_ids = fields.Many2many('forlife.bom', string='Declare BOM')

    def action_open_bom(self):
        req_id = self.forlife_production_id.id
        current_bom = self.env['forlife.bom'].search([('forlife_production_id', '=', req_id), ('product_id', '=', self.product_id.id)], limit=1)
        return {
            'name': ('BOM'),
            'view_mode': 'form',
            'view_id': self.env.ref('forlife_purchase.forlife_bom_form').id,
            'res_model': 'forlife.bom',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': current_bom.id,
        }

    @api.constrains('produce_qty', 'stock_qty')
    def constrains_stock_qty_produce_qty(self):
        for rec in self:
            if rec.produce_qty < 0:
                raise ValidationError('Số lượng sản xuất không được âm!')
            elif rec.stock_qty < 0:
                raise ValidationError('Số lượng nhập kho không được âm!')
            elif rec.produce_qty < rec.stock_qty:
                raise ValidationError('Số lượng sản xuất phải lớn hơn số lượng nhập kho!!')



class ForlifeProductionMaterial(models.Model):
    _name = 'forlife.production.material'
    _description = 'Forlife Production Material'

    forlife_production_id = fields.Many2one('forlife.production', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    quantity = fields.Integer()
    uom_id = fields.Many2one('uom.uom', string='Uom Whs')


class ForlifeProductionServiceCost(models.Model):
    _name = 'forlife.production.service.cost'
    _description = 'Forlife Production Service Cost'

    forlife_production_id = fields.Many2one('forlife.production', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    prices = fields.Monetary()
