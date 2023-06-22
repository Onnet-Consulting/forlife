from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if 'endloop' in self._context and self._context.get('endloop'):
            return res
        ec_warehouse_id = self.env.ref('forlife_stock.sell_ecommerce', raise_if_not_found=False).id
        if self.sale_id.source_record and self.company_id.code == '1300' and self.picking_type_code == 'outgoing' and not self.x_is_check_return \
            and self.location_id.stock_location_type_id.id == ec_warehouse_id:
            data = []
            if self.company_id.code == '1300':
                location_mapping = self.env['stock.location.mapping'].sudo().search([('location_id', '=', self.location_id.id)])
                if not location_mapping:
                    raise UserError(
                        _(f"Vui lòng cấu hình liên kết cho địa điểm {self.location_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
                for line in self.move_ids_without_package:
                    product = line.product_id
                    data.append((0, 0, {
                        'product_id': product.id,
                        'location_id': location_mapping.location_map_id.id,
                        'location_dest_id': self.env.ref('forlife_inventory.xuat_ki_gui_tu_dong',raise_if_not_found=False).id,
                        'name': product.display_name,
                        'date': datetime.now(),
                        'product_uom': line.uom_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'quantity_done': line.quantity_done,
                        'amount_total': 0,
                        'company_id': location_mapping.location_map_id.company_id.id
                    }))
                # if self.sale_id.nhanh_id and self.company_id.code == '1300':
                orther_export = self.env['stock.picking'].with_company(location_mapping.location_map_id.company_id).create({
                    'reason_type_id': self.env.ref('forlife_inventory.reason_type_export_auto', raise_if_not_found=False).id,
                    'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
                    'location_id': location_mapping.location_map_id.id,
                    'location_dest_id': self.env.ref('forlife_inventory.xuat_ki_gui_tu_dong', raise_if_not_found=False).id,
                    'other_export': True,
                    'move_ids_without_package': data,
                })
                orther_export.with_context(endloop=True).button_validate()
        if self.sale_id.source_record and self.company_id.code == '1300' and self.picking_type_code == 'incoming' and self.x_is_check_return and self.location_dest_id.stock_location_type_id.id == ec_warehouse_id:
            data = []
            location_mapping = self.env['stock.location.mapping'].sudo().search(
                [('location_id', '=', self.location_dest_id.id)])
            if not location_mapping:
                raise UserError(
                    _(f"Vui lòng cấu hình liên kết cho địa điểm {self.location_dest_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
            for line in self.move_line_ids_without_package:
                product = line.product_id
                data.append((0, 0, {
                    'product_id': product.id,
                    'location_id': self.env.ref('forlife_inventory.nhap_ki_gui_tu_dong', raise_if_not_found=False).id,
                    'location_dest_id': location_mapping.location_map_id.id,
                    'name': product.display_name,
                    'date': datetime.now(),
                    'product_uom': line.product_uom_id.id,
                    'product_uom_qty': line.qty_done,
                    'quantity_done': line.qty_done,
                    'amount_total': 0,
                    'company_id': location_mapping.location_map_id.company_id.id
                }))
            # if self.sale_id.nhanh_id and self.company_id.code == '1300':
            other_import = self.env['stock.picking'].with_company(location_mapping.location_map_id.company_id).create({
                'reason_type_id': self.env.ref('forlife_inventory.reason_type_import_auto', raise_if_not_found=False).id,
                'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
                'location_id': self.env.ref('forlife_inventory.nhap_ki_gui_tu_dong', raise_if_not_found=False).id,
                'location_dest_id': location_mapping.location_map_id.id,
                'other_import': True,
                'move_ids_without_package': data,
            })
            other_import.with_context(endloop=True).button_validate()
        return res

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        pickings = super(StockPicking, self)._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type,
                                                                                 partner)
        Picking = self.env['stock.picking']
        stockable_lines = lines.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty,
                                                                                      precision_rounding=l.product_id.uom_id.rounding))
        if not stockable_lines:
            return Picking
        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines
        data = []
        if negative_lines:
            for picking in pickings:
                if picking.location_dest_id.id:
                    location_mapping = self.env['stock.location.mapping'].sudo().search(
                        [('location_map_id', '=', picking.location_dest_id.id)])
                    location_id = self.env.ref('forlife_inventory.nhap_tra_lai_hang_ki_gui_tu_dong', raise_if_not_found=False)
                    if location_mapping and location_mapping.location_id.id_deposit and location_mapping.location_id.account_stock_give:
                        company = location_mapping.location_id.warehouse_id.company_id.id
                        for line in picking.move_ids_without_package:
                            product = line.product_id
                            data.append((0, 0, {
                                'product_id': product.id,
                                'location_id': location_id.id,
                                'location_dest_id': location_mapping.location_id.id,
                                'name': product.display_name,
                                'date': datetime.now(),
                                'product_uom': line.uom_id.id,
                                'product_uom_qty': line.product_uom_qty,
                                'quantity_done': line.quantity_done,
                                'amount_total': line.quantity_done * line.product_id.with_company(company).standard_price
                            }))
                        pickking_ortherimport = Picking.with_company(company).create({
                            'reason_type_id': self.env.ref('forlife_inventory.reason_type_import_return_product', raise_if_not_found=False).id,
                            'picking_type_id': location_mapping.location_id.warehouse_id.int_type_id.id,
                            'location_id': location_id.id,
                            'location_dest_id': location_mapping.location_id.id,
                            'other_import': True,
                            'move_ids_without_package': data,
                        })
                        pickking_ortherimport.button_validate()
        return pickings
