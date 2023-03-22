from odoo import fields, models, api, _
from odoo.exceptions import AccessError, ValidationError


class ForlifeMrpBom(models.Model):
    _name = 'forlife.mrp.bom'

    forlife_production_id = fields.Many2one('forlife.production')
    product_id = fields.Many2one('product.product')
    price = fields.Float(related="product_id.lst_price")

    description = fields.Char(string='Description')
    quantity = fields.Integer(string="Quantity")
    uom_id = fields.Many2one(related="product_id.uom_id")

    amount_total = fields.Integer('Total')
    materials_line = fields.One2many('forlife.mrp.bom.nvl.line', 'mrp_bom_id')
    cost_line = fields.One2many('forlife.mrp.bom.cost.line', 'mrp_bom_id')

    @api.depends('price', 'quantity')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.quantity * rec.price

class ForlifeMrpBomNvlLine(models.Model):
    _name = "forlife.mrp.bom.nvl.line"

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    colour = fields.Char(string='Colour')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    quantity = fields.Float(string='Quantity')
    loss = fields.Float(string='Loss %')
    coefficient_exchange = fields.Float(string='Coefficient Exchange')
    plant = fields.Float(string='Plant')
    demand_m = fields.Float(string='Demand (m)')
    demand_kg = fields.Float(string='Demand (kg)')
    warehouse = fields.Many2one('hr.department', string="Warehouse")
    prices_total = fields.Float(string='Prices Total')
    price_update_date = fields.Date(string="Date")

    mrp_bom_id = fields.Many2one('forlife.mrp.bom')

    #     # @api.depends('plant', 'quantity', 'loss')
    #     # def compute_demand_m(self):
    #     #     for rec in self:
    #     #         rec.demand_m = rec.plant * rec.quantity * rec.loss * 0.01
    #     #
    #     # @api.depends('demand_m', 'coefficient_exchange')
    #     # def compute_demand_kg(self):
    #     #     for rec in self:
    #     #         rec.demand_kg = rec.demand_m * rec.coefficient_exchange
class ForlifeMrpBomCostLine(models.Model):
    _name = "forlife.mrp.bom.cost.line"

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    uom_id = fields.Many2one(related="product_id.uom_id", string="UoM")
    quantity = fields.Float(string='Quantity')
    prices = fields.Float(string='Prices')
    total = fields.Float(string='Total')
    prices_total = fields.Float(string='Prices Total')
    price_update_date = fields.Date(string="Date")

    mrp_bom_id = fields.Many2one('forlife.mrp.bom')