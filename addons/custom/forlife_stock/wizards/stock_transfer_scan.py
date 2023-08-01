from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockTransferScan(models.TransientModel):
    _name = 'stock.transfer.scan'
    _description = "Stock Transfer Scan"

    transfer_id = fields.Many2one(comodel_name='stock.transfer', required=True)
    barcode = fields.Char('Barcode')
    stock_transfer_scan_line_ids = fields.One2many(comodel_name='stock.transfer.scan.line', inverse_name='stock_transfer_scan_id', readonly=True)
    note = fields.Char(readonly=True)

    @api.onchange('barcode')
    def onchange_barcode(self):
        if self.barcode:
            line = self.stock_transfer_scan_line_ids.filtered(lambda r: r.barcode == self.barcode)
            if line:
                if line[0].product_qty_done + 1 > line[0].max_qty:
                    self.note = 'Số lượng quét "%s" đang vượt quá số lượng tối đa!' % self.barcode
                else:
                    self.note = None
                    line[0].update({'product_qty_done': (line[0].product_qty_done or 0) + 1})
            else:
                self.note = 'Barcode "%s" không hợp lệ!' % self.barcode
            self.barcode = None

    def action_update(self):

        # Khi trạng thái là 'Đã phê duyệt' => update số lượng quét vào Số lượng xuất
        if self.transfer_id.state == 'approved':
            for line in self.stock_transfer_scan_line_ids:
                line.transfer_line_id.qty_out = line.product_qty_done

        # Khi trạng thái là 'Xác nhận xuất' => update số lượng quét vào Số lượng nhập
        if self.transfer_id.state == 'out_approve':
            for line in self.stock_transfer_scan_line_ids:
                line.transfer_line_id.qty_in = line.product_qty_done


class StockTransferScanLine(models.TransientModel):
    _name = 'stock.transfer.scan.line'
    _description = "Stock Transfer Scan line"

    stock_transfer_scan_id = fields.Many2one(comodel_name='stock.transfer.scan', ondelete='cascade')
    transfer_line_id = fields.Many2one(comodel_name='stock.transfer.line', required=True, string='Sản phẩm')
    barcode = fields.Char(related='transfer_line_id.product_id.barcode')
    qty_plan = fields.Integer(related='transfer_line_id.qty_plan', string='Số lượng điều chuyển')
    max_qty = fields.Integer(string='Số lượng tối đa')
    product_qty_done = fields.Integer(string='Số lượng đã quét')
