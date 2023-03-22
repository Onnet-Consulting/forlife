from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
import json
from io import BytesIO
import xlsxwriter
import base64


class TransferStockInventory(models.Model):
    _name = 'transfer.stock.inventory'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Transfer Stock Inventory'
    _rec_name = 'code'

    code = fields.Char(string="Code", default='New', copy=False)
    employee_id = fields.Many2one('hr.employee', string="User")
    location_id = fields.Many2one('stock.location', string='Location')
    note = fields.Text(string="Note")
    transfer_stock_inventory_line_ids = fields.One2many('transfer.stock.inventory.line', 'transfer_stock_inventory_id')
    state = fields.Selection(
        tracking=True,
        string="Status",
        selection=[('draft', 'Draft'),
                   ('wait_confirm', 'Wait Confirm'),
                   ('approved', 'Approved'),
                   ('reject', 'Reject'),
                   ('cancel', 'Cancel'),
                   ('done', 'Done')], default='draft', copy=True)
    reason_reject = fields.Text('Reason Reject')
    reason_cancel = fields.Text('Reason Cancel')

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['employee_id'] = self.env.user.employee_id.id if self.env.user.employee_id else False
        res['create_date'] = datetime.now()
        return res

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('transfer.stock.inventory.name.sequence') or 'TSI'
        return super(TransferStockInventory, self).create(vals)

    def action_wait_confirm(self):
        for rec in self:
            rec.write({'state': 'wait_confirm'})

    def action_approve(self):
        for rec in self:
            rec.write({'state': 'approved'})

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})

    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})




class TransferStockInventoryLine(models.Model):
    _name = "transfer.stock.inventory.line"

    transfer_stock_inventory_id = fields.Many2one('transfer.stock.inventory')
    product_from_id = fields.Many2one('product.product', string= 'Product From')
    uom_from_id = fields.Many2one('uom.uom', string='Uom', related='product_from_id.uom_id')
    qty_out = fields.Integer(string="Quantity Out")
    unit_price_from = fields.Float(string="Unit Price", related='product_from_id.standard_price')
    total_out = fields.Float(string='Total Out', compute='compute_total_out')
    product_to_id = fields.Many2one('product.product', string="Product To")
    uom_to_id = fields.Many2one('uom.uom', string='Uom', related='product_to_id.uom_id')
    location_id = fields.Many2one('stock.location', string='Location')
    qty_in = fields.Integer(string="Quantity In")
    unit_price_to = fields.Float(string="Unit Price", related='product_from_id.standard_price')
    total_in = fields.Float(string='Total In', compute='compute_total_in')

    @api.depends('qty_out', 'unit_price_from')
    def compute_total_out(self):
        for item in self:
                item.total_out = item.qty_out * item.unit_price_from

    @api.depends('qty_in', 'unit_price_to')
    def compute_total_in(self):
        for item in self:
            item.total_in = item.qty_in * item.unit_price_to