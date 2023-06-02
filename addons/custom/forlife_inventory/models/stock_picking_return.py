from odoo import api, fields, models,_
from datetime import date, datetime
from odoo.exceptions import UserError

class Return(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        if self.picking_id.sale_id.nhanh_id and self.picking_id.company_id.code == '1300':
            data = []
            if self.company_id.code == '1300':
                location_mapping = self.env['stock.location.mapping'].sudo().search(
                    [('location_id', '=', self.picking_id.location_id.id)])
                if not location_mapping:
                    raise UserError(
                        _(f"Vui lòng cấu hình liên kết cho địa điểm {self.picking_id.location_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
                for line in self.product_return_moves:
                    product = line.product_id
                    data.append((0, 0, {
                        'product_id': product.id,
                        'location_id': location_mapping.location_map_id.id,
                        'location_dest_id': self.env.ref('forlife_inventory.xuat_ki_gui_tu_dong', raise_if_not_found=False).id,
                        'name': product.display_name,
                        'date': datetime.now(),
                        'product_uom': line.uom_id.id,
                        'product_uom_qty': line.quantity,
                        'quantity_done': line.quantity,
                        'amount_total': line.quantity * line.product_id.standard_price,
                        'company_id': location_mapping.location_map_id.company_id.id
                    }))
                # if self.sale_id.nhanh_id and self.company_id.code == '1300':
                other_import = self.env['stock.picking'].with_company(location_mapping.location_map_id.company_id).create({
                    'reason_type_id': self.env.ref('forlife_inventory.reason_type_export_auto', raise_if_not_found=False).id,
                    'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
                    'location_id': location_mapping.location_map_id.id,
                    'location_dest_id': self.env.ref('forlife_inventory.xuat_ki_gui_tu_dong', raise_if_not_found=False).id,
                    'other_import': True,
                    'move_ids_without_package': data,
                })
                other_import.button_validate()
        return super(Return, self).create_returns()