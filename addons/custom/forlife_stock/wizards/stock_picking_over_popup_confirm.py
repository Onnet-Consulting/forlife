from odoo import api, fields, models
from datetime import date, datetime, timedelta, time

class StockPickingOverPopupConfirm(models.TransientModel):
    _name = 'stock.picking.over.popup.confirm'
    _description = 'Stock Picking Over Popup Confirm'

    picking_id = fields.Many2one('stock.picking')

    def process(self):
        self.ensure_one()
        list_line_over = []
        for pk, pk_od in zip(self.picking_id.move_line_ids_without_package, self.picking_id.move_ids_without_package):
            tolerance_id = pk.product_id.tolerance_ids.filtered(lambda x: x.partner_id.id == self.picking_id.purchase_id.partner_id.id)
            if tolerance_id:
                tolerance = tolerance_id.sorted(key=lambda x: x.id, reverse=False)[-1].mapped('tolerance')[0]
            else:
                tolerance = 0
            if pk.qty_done != pk_od.product_uom_qty:
                if pk.qty_done > pk_od.product_uom_qty:
                    product_uom_qty = (pk_od.product_uom_qty * (1 + (tolerance / 100))) if tolerance else pk_od.product_uom_qty
                    if pk.qty_done != product_uom_qty:
                        list_line_over.append((0, 0, {
                            'product_id': pk_od.product_id.id,
                            'product_uom_qty': pk.qty_done - product_uom_qty,
                            'quantity_done': pk.qty_done - product_uom_qty,
                            'product_uom': pk_od.product_uom.id,
                            'free_good': pk_od.free_good,
                            'quantity_change': pk_od.quantity_change,
                            'quantity_purchase_done': (pk.qty_done - product_uom_qty)/(pk_od.quantity_change),
                            'occasion_code_id': pk.occasion_code_id.id,
                            'work_production': pk.work_production.id,
                            'account_analytic_id': pk.account_analytic_id.id,
                            'price_unit': pk_od.price_unit,
                            'location_id': pk_od.location_id.id,
                            'location_dest_id': pk_od.location_dest_id.id,
                            'amount_total': pk_od.amount_total,
                            'reason_type_id': pk_od.reason_type_id.id,
                            'reason_id': pk_od.reason_id.id,
                            'purchase_line_id': pk_od.purchase_line_id.id,
                        }))

            if pk.qty_done > pk_od.product_uom_qty:
                pk.write({
                    'qty_done': (pk_od.product_uom_qty * (1 + (tolerance / 100))) if tolerance else pk_od.product_uom_qty,
                })
                pk_od.write({
                    'product_uom_qty': (pk_od.product_uom_qty * (1 + (tolerance / 100))) if tolerance else pk_od.product_uom_qty,
                })

        if list_line_over:
            master_data_over = {
                'reason_type_id': self.picking_id.reason_type_id.id,
                'location_id': self.picking_id.location_id.id,
                'partner_id': self.picking_id.partner_id.id,
                'location_dest_id': self.picking_id.location_dest_id.id,
                'scheduled_date': datetime.now(),
                'origin': self.picking_id.origin,
                'is_pk_purchase': self.picking_id.is_pk_purchase,
                'leftovers_id': self.picking_id.id,
                'state': 'assigned',
                'other_import_export_request_id': self.picking_id.other_import_export_request_id.id,
                'picking_type_id': self.picking_id.picking_type_id.id,
                'move_ids_without_package': list_line_over,
            }
            data_pk_over = self.env['stock.picking'].create(master_data_over)

            for pk, pk_od in zip(data_pk_over.move_line_ids_without_package, self.picking_id.move_line_ids_without_package):
                pk.write({
                    'quantity_change': pk_od.quantity_change,
                    'quantity_purchase_done': pk.qty_done/pk_od.quantity_change
                })
            for pk in self.picking_id.move_line_ids:
                pk.write({
                        'quantity_purchase_done': pk.qty_done/pk.quantity_change
                    })
            for pk in self.picking_id.move_ids:
                pk.write({
                        'quantity_purchase_done': pk.quantity_done/pk.quantity_change
                    })
        return self.picking_id.button_validate()
