from odoo import api, fields, models,_
from odoo.exceptions import UserError, ValidationError

class StockTranfer(models.Model):
    _inherit = 'stock.transfer'


    def _create_stock_picking_other_import_and_export(self, data, location_id, location_dest_id):
        # fetch-data-to-compare

        warehouse_type_id_tl = self.env.ref('forlife_base.stock_warehouse_type_03', raise_if_not_found=False).id
        warehouse_type_id_fm = self.env.ref('forlife_base.stock_warehouse_type_04', raise_if_not_found=False).id
        warehouse_type_id_ec = self.env['stock.warehouse.type'].sudo().search([('code', '=', 5)])
        warehouse_type_id_ec = warehouse_type_id_ec.id if warehouse_type_id_ec else 0
        warehouse_type_master = self.env.ref('forlife_base.stock_warehouse_type_01', raise_if_not_found=False).id
        s_location_pos = self.env.ref('forlife_stock.warehouse_for_pos', raise_if_not_found=False).id
        s_location_error = self.env.ref('forlife_stock.warehouse_error', raise_if_not_found=False).id
        s_location_sell_ecommerce = self.env.ref('forlife_stock.sell_ecommerce', raise_if_not_found=False).id
        warehouse_id = location_id.warehouse_id.whs_type.id
        warehouse_dest_id = location_dest_id.warehouse_id.whs_type.id
        s_location_type_id = location_id.stock_location_type_id.id
        s_location_dest_type_id = location_dest_id.stock_location_type_id.id
        if location_id.company_id.code == '1300' or location_dest_id.company_id.code == '1300':
            if warehouse_dest_id in [warehouse_type_id_tl, warehouse_type_id_fm] and warehouse_id in [
                warehouse_type_master, warehouse_type_id_ec] \
                    and (s_location_dest_type_id == s_location_pos or s_location_dest_type_id == s_location_sell_ecommerce):
                location_mapping = self.env['stock.location.mapping'].sudo().search(
                    [('location_id', '=', location_dest_id.id)])

                self._create_orther_import_export(location_mapping, data, type='import', location=location_dest_id)

            elif warehouse_dest_id in [warehouse_type_master, warehouse_type_id_ec] and warehouse_id in [
                warehouse_type_id_tl, warehouse_type_id_fm] \
                    and (s_location_type_id == s_location_pos or s_location_type_id == s_location_sell_ecommerce):

                location_mapping = self.env['stock.location.mapping'].sudo().search(
                    [('location_id', '=', location_id.id)])

                self._create_orther_import_export(location_mapping, data, type='export', location=location_id)

            else:
                return False
        else:
            return False
        return True

    def _create_orther_import_export(self, location_mapping, data, type, location):
        if location_mapping:
            company = location_mapping.location_map_id.warehouse_id.company_id.id
            if type == 'import':
                for data_line in data:
                    data_line[2].update({'location_id': self.env.ref('forlife_inventory.nhap_ki_gui_tu_dong', raise_if_not_found=False).id,
                                         'location_dest_id': location_mapping.location_map_id.id})
                stock_picking = self.env['stock.picking'].with_company(company).create({
                    'transfer_id': self.id,
                    'reason_type_id':self.env.ref('forlife_inventory.reason_type_import_auto').id,
                    'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
                    'location_id': self.env.ref('forlife_inventory.nhap_ki_gui_tu_dong').id,
                    'location_dest_id': location_mapping.location_map_id.id,
                    'move_ids_without_package': data,
                    'other_import': True
                })
            else:
                for data_line in data:
                    data_line[2].update({'location_id': location_mapping.location_map_id.id,
                                         'location_dest_id': self.env.ref('forlife_inventory.xuat_ki_gui_tu_dong', raise_if_not_found=False).id})
                stock_picking = self.env['stock.picking'].with_company(company).create({
                    'transfer_id': self.id,
                    'reason_type_id': self.env.ref('forlife_inventory.reason_type_export_auto').id,
                    'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
                    'location_id': location_mapping.location_map_id.id,
                    'location_dest_id': self.env.ref('forlife_inventory.xuat_ki_gui_tu_dong', raise_if_not_found=False).id,
                    'move_ids_without_package': data,
                    'other_export': True
                })
            stock_picking.button_validate()
            return stock_picking
        else:
            raise UserError(
                _(f"Vui lòng cấu hình liên kết cho địa điểm {location.name_get()[0][1]} Cấu hình -> Location Mapping!"))

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        records = self.browse()
        warehouse_type_id_tl = self.env.ref('forlife_base.stock_warehouse_type_03', raise_if_not_found=False).id
        warehouse_type_id_fm = self.env.ref('forlife_base.stock_warehouse_type_04', raise_if_not_found=False).id
        warehouse_type_id_ec = self.env['stock.warehouse.type'].sudo().search([('code', '=', 5)])
        warehouse_type_id_ec = warehouse_type_id_ec.id if warehouse_type_id_ec else 0
        s_location_pos = self.env.ref('forlife_stock.warehouse_for_pos', raise_if_not_found=False).id
        s_location_error = self.env.ref('forlife_stock.warehouse_error', raise_if_not_found=False).id
        s_location_sell_ecommerce = self.env.ref('forlife_stock.sell_ecommerce', raise_if_not_found=False).id
        for vals in vals_list:
            new_vals_list.append(vals)
            vals_sync = vals.copy()
            location_id = self.env['stock.location'].sudo().search([('id', '=', vals['location_id'])])
            location_dest_id = self.env['stock.location'].sudo().search([('id', '=', vals['location_dest_id'])])
            warehouse_id = location_id.warehouse_id.whs_type.id
            warehouse_dest_id = location_dest_id.warehouse_id.whs_type.id
            s_location_type_id = location_id.stock_location_type_id.id
            s_location_dest_type_id = location_dest_id.stock_location_type_id.id
            if warehouse_id in [warehouse_type_id_tl, warehouse_type_id_fm,
                                warehouse_type_id_ec] and warehouse_dest_id in [warehouse_type_id_tl,
                                                                                warehouse_type_id_fm,
                                                                                warehouse_type_id_ec] \
                    and s_location_type_id in [s_location_pos, s_location_error,
                                               s_location_sell_ecommerce] and s_location_dest_type_id in [
                s_location_pos, s_location_error, s_location_sell_ecommerce]:
                location_mapping = self.env['stock.location.mapping'].search(
                    [('location_map_id', '=', vals['location_id'])])
                location_dest_mapping = self.env['stock.location.mapping'].search(
                    [('location_map_id', '=', vals['location_dest_id'])])
                if location_mapping and location_dest_mapping:
                    vals_sync['location_id'] = location_mapping.location_id.id
                    vals_sync['location_dest_id'] = location_dest_mapping.location_id.id
                    warehouse_sync = self.env['stock.location'].browse(vals.get('location_id')).code
                    vals_sync['name'] = self.env['ir.sequence'].next_by_code('stock.transfer.sequence') + (
                        warehouse_sync if warehouse_sync else '' + str(datetime.now().year)) or 'PXB'
                    new_vals_list.append(vals_sync)
                else:
                    return super(StockTranfer, self).create(vals_list)
        vals_list = new_vals_list
        records |= super().create(vals_list)
        return records[0]
