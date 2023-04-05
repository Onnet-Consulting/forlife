# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ForlifeProduction(models.Model):
    _name = 'forlife.production'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Forlife Production"
    _rec_name = 'code'

    # name = fields.Char("Name")
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
        ('open', 'Open'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft')

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


class ForlifeProductionFinishedProduct(models.Model):
    _name = 'forlife.production.finished.product'
    _description = 'Forlife Production Finished Product'

    forlife_production_id = fields.Many2one('forlife.production', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', related='product_id.uom_id')
    produce_qty = fields.Float(string='Produce Quantity', required=True)
    unit_price = fields.Float(readonly=1)
    stock_qty = fields.Float(string='Stock Quantity')
    remaining_qty = fields.Float(string='Remaining Quantity')
    description = fields.Char(String='Description', related='product_id.name')
    forlife_bom_ids = fields.Many2many('forlife.bom', string='Declare BOM')

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
