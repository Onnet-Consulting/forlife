from odoo import api, fields, models


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    def create_import_export_other(self, vals, type_picking):
        notifi = False
        if self.inventory_id.company_id.code == '1400':
            if type_picking == 'import':
                location_mapping = self.env['stock.location.mapping'].search(
                    [('location_map_id', '=', vals['location_id'])])
            else:
                location_mapping = self.env['stock.location.mapping'].search(
                    [('location_map_id', '=', vals['location_dest_id'])])
            if not location_mapping:
                notifi = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'message': 'Có địa điểm chưa được cấu hình : Cấu hình -> Location Mapping!',
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
            else:
                print('3333333')
                raise
                product = self.env['product.product'].search([('id', '=', vals['product_id'])])
                if type_picking == 'import':
                    picking = self.env['stock.picking'].with_company(location_mapping.location_id.company_id).create({
                        'reason_type_id': self.env.ref('forlife_stock.reason_type_5', raise_if_not_found=False).id,
                        'picking_type_id': location_mapping.location_id.warehouse_id.int_type_id.id,
                        'location_id': self.env.ref('forlife_stock.enter_inventory_balance_auto',
                                                    raise_if_not_found=False).id,
                        'location_dest_id': location_mapping.location_id.id,
                        'other_import': True,
                        'move_ids_without_package': [(0, 0, {
                            'product_id': product.id,
                            'location_id': self.env.ref('forlife_stock.enter_inventory_balance_auto',
                                                        raise_if_not_found=False).id,
                            'location_dest_id': location_mapping.location_id.id,
                            'name': vals['name'],
                            'date': datetime.now(),
                            'product_uom': vals['product_uom'],
                            'product_uom_qty': vals['product_uom_qty'],
                            'quantity_done': vals['product_uom_qty'],
                            'amount_total': vals['product_uom_qty'] * product.standard_price
                        })],
                    })
                    picking.button_validate()
                else:
                    picking = self.env['stock.picking'].with_company(location_mapping.location_id.company_id).create({
                        'reason_type_id': self.env.ref('forlife_stock.reason_type_5', raise_if_not_found=False).id,
                        'picking_type_id': location_mapping.location_id.warehouse_id.int_type_id.id,
                        'location_id': location_mapping.location_id.id,
                        'location_dest_id': self.env.ref('forlife_stock.enter_inventory_balance_auto',
                                                         raise_if_not_found=False).id,
                        'other_export': True,
                        'move_ids_without_package': [(0, 0, {
                            'product_id': product.id,
                            'location_id': location_mapping.location_id.id,
                            'location_dest_id': self.env.ref('forlife_stock.enter_inventory_balance_auto',
                                                             raise_if_not_found=False).id,
                            'name': vals['name'],
                            'date': datetime.now(),
                            'product_uom': vals['product_uom'],
                            'product_uom_qty': vals['product_uom_qty'],
                            'quantity_done': vals['product_uom_qty'],
                            'amount_total': vals['product_uom_qty'] * product.standard_price
                        })],
                    })
                    picking.button_validate()
            return notifi
        return notifi
