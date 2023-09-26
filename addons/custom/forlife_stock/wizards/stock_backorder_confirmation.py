from odoo import api, fields, models, _


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        res = super().process()
        for item in self:
            for rec in item.pick_ids:
                backorder_id = self.env['stock.picking'].search([('backorder_id', '=', rec.id)])
                for move_line_id in backorder_id.move_line_ids_without_package:
                    if move_line_id.quantity_change:
                        if move_line_id.quantity_purchase_done:
                            move_line_id.qty_done = move_line_id.quantity_change * move_line_id.quantity_purchase_done
                        else:
                            move_line_id.update({
                                'qty_done': move_line_id.reserved_qty,
                                'quantity_purchase_done': move_line_id.reserved_qty / move_line_id.quantity_change,
                            })
                            move_line_id.move_id.update({
                                'quantity_purchase_done': move_line_id.reserved_qty / move_line_id.quantity_change
                            })
                    else:
                        move_line_id.qty_done = move_line_id.reserved_qty

                # for pk, pk_od in zip(data_pk.move_line_ids_without_package, rec.move_line_ids_without_package):
                #     qty_done = pk.reserved_qty if pk.reserved_qty else pk.move_id.product_uom_qty
                #     pk.write({
                #         'po_id': pk_od.po_id,
                #         'qty_done': qty_done,
                #         'quantity_change': pk_od.quantity_change,
                #         'quantity_purchase_done': pk.reserved_qty / pk_od.quantity_change if pk_od.quantity_change else 1
                #     })
                # for pk, pk_od in zip(rec.move_line_ids_without_package, rec.move_ids_without_package):
                #     pk_od.write({
                #         'quantity_purchase_done': pk.quantity_purchase_done,
                #     })
                # for pk, pk_od in zip(data_pk.move_line_ids_without_package, data_pk.move_ids_without_package):
                #     pk_od.write({
                #         'quantity_purchase_done': pk.quantity_purchase_done,
                #     })
        return res
