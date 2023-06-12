# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class StockWarehouseType(models.Model):
    _name = 'stock.warehouse.type'
    _inherit = "forlife.model.mixin"
    _description = "Type of Warehouse"


class StockWarehouseStatus(models.Model):
    _name = 'stock.warehouse.status'
    _inherit = "forlife.model.mixin"
    _description = "Status of Warehouse"


class ResForlifeBrand(models.Model):
    _name = 'res.forlife.brand'
    _inherit = "forlife.model.mixin"
    _description = "Brand"


class ResSaleProvince(models.Model):
    _name = 'res.sale.province'
    _inherit = "forlife.model.mixin"
    _description = "Sale Province"


class ResLocationProvince(models.Model):
    _name = 'res.location.province'
    _inherit = "forlife.model.mixin"
    _description = "Location Province"


class ResWeatherProvince(models.Model):
    _name = 'res.weather.province'
    _inherit = "forlife.model.mixin"
    _description = "Weather Province"


class ResStateDistrict(models.Model):
    _name = 'res.state.district'
    _inherit = "forlife.model.mixin"
    _description = "District"

    state_id = fields.Many2one('res.country.state', string='State', required=True)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    warehouse_code_internal = fields.Char(string="Code Internal")
    name_internal = fields.Char(string="Name Internal")
    short_name_internal = fields.Char(string="Short Name Internal")
    brand_id = fields.Many2one('res.brand', string="Brand", copy=False)
    square = fields.Char(string="Square", copy=False)
    phone = fields.Char(string="Phone", copy=False)
    sale_province_id = fields.Many2one("res.sale.province", string="Sale Province", copy=False)
    loc_province_id = fields.Many2one("res.location.province", string="Location Province", copy=False)
    weather_province_id = fields.Many2one("res.weather.province", string="Weather Province", copy=False)
    manager_id = fields.Many2one('hr.employee', string="Manager", copy=False)
    status_ids = fields.Many2one('stock.warehouse.status', string="Status", copy=False)
    district_id = fields.Many2one('res.state.district', string="District", copy=False)
    ward_id = fields.Many2one('res.ward', string="Ward", copy=False)
    warehouse_gr_id = fields.Many2one('warehouse.group', 'Nhóm kho')


class StockWarehouseGroup(models.Model):
    _name = 'warehouse.group'

    _description = 'Nhóm kho'

    code_level_1 = fields.Char(string='Mã nhóm kho')
    name = fields.Char('Tên nhóm kho')
    parent_warehouse_group_id = fields.Many2one('warehouse.group', 'Nhóm kho cha')

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code_level_1)', 'Mã phải là duy nhất!')
    ]