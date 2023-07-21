from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockPickingScan(models.TransientModel):
    _name = 'stock.picking.scan'
    _description = "Stock Picking Scan"

    picking_id = fields.Many2one(comodel_name='stock.picking', required=True)
    barcode = fields.Char('Barcode')
    stock_picking_scan_line_ids = fields.One2many(comodel_name='stock.picking.scan.line', inverse_name='stock_picking_scan_id', readonly=True)
    note = fields.Char(readonly=True)

    @api.onchange('barcode')
    def onchange_barcode(self):
        if self.barcode:
            line = self.stock_picking_scan_line_ids.filtered(lambda r: r.barcode == self.barcode)
            if line:
                self.note = None
                line[0].update({'product_qty_done': (line[0].product_qty_done or 0) + 1})
            else:
                self.note = 'Barcode "%s" không hợp lệ!' % self.barcode
            self.barcode = None

    def action_update(self):
        for line in self.stock_picking_scan_line_ids:
            if line.move_line_id.qty_done != line.product_qty_done:
                line.move_line_id.write({'qty_done': line.product_qty_done})


class StockPickingScanLine(models.TransientModel):
    _name = 'stock.picking.scan.line'
    _description = "Stock Picking Scan line"

    stock_picking_scan_id = fields.Many2one(comodel_name='stock.picking.scan', ondelete='cascade')
    move_line_id = fields.Many2one(comodel_name='stock.move.line', required=True, string='Sản phẩm')
    barcode = fields.Char(related='move_line_id.product_id.barcode')
    product_uom_qty = fields.Float(related='move_line_id.move_id.product_uom_qty', string='Số lượng yêu cầu')
    product_qty_done = fields.Float(string='Số lượng đã quét')




