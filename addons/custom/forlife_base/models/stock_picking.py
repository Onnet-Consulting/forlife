from odoo import models, fields, api


class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    is_need_scan_barcode = fields.Boolean(compute='_compute_need_scan_barcode', store=True)

    @api.depends(
        'move_line_ids_without_package',
        'move_line_ids_without_package.product_id',
        'move_line_ids_without_package.product_id.is_need_scan_barcode'
    )
    def _compute_need_scan_barcode(self):
        for rec in self:
            rec.is_need_scan_barcode = any(sm.product_id.is_need_scan_barcode for sm in rec.move_ids_without_package)


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    is_need_scan_barcode = fields.Boolean(compute='_compute_need_scan_barcode', compute_sudo=True, store=True)

    @api.depends('product_id', 'product_id.is_need_scan_barcode')
    def _compute_need_scan_barcode(self):
        for rec in self:
            rec.is_need_scan_barcode = rec.product_id.is_need_scan_barcode


class InheritStockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_need_scan_barcode = fields.Boolean(related='move_id.is_need_scan_barcode', compute_sudo=True)
