from odoo import models, fields, api


class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    is_need_scan_barcode = fields.Boolean()

    # @api.depends(
    #     'move_ids_without_package',
    #     'move_ids_without_package.product_id',
    #     'move_ids_without_package.product_id.is_need_scan_barcode'
    # )
    @api.depends('move_ids_without_package')
    def _compute_need_scan_barcode(self):
        for rec in self:
            rec.is_need_scan_barcode = any(sm.is_need_scan_barcode for sm in rec.move_ids_without_package)


class InheritStockMove(models.Model):
    _inherit = 'stock.move'

    is_need_scan_barcode = fields.Boolean()

    @api.depends('product_id', 'product_id.is_need_scan_barcode')
    def _compute_need_scan_barcode(self):
        for rec in self:
            rec.is_need_scan_barcode = rec.product_id.is_need_scan_barcode


class InheritStockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_need_scan_barcode = fields.Boolean()

    @api.depends('product_id', 'product_id.is_need_scan_barcode')
    def _compute_need_scan_barcode(self):
        for rec in self:
            rec.is_need_scan_barcode = rec.product_id.is_need_scan_barcode
