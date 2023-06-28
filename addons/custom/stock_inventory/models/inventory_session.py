# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class InventorySession(models.Model):
    _name = 'inventory.session'
    _description = 'Inventory Session'
    _rec_name = 'inv_id'

    inv_id = fields.Many2one('stock.inventory', 'Stock Inventory', ondelete='restrict')
    note = fields.Char('Note')
    active = fields.Boolean('Active', default=True)
    data = fields.Binary('Data')
