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

    def create_tranfer_with_type_kigui(self):
        company = self.env['res.company'].sudo().search([('id', '=', self._context.get('company_match'))])
        warehouse_type_id_tl = self.env.ref('forlife_base.stock_warehouse_type_03', raise_if_not_found=False).id
        warehouse_type_id_fm = self.env.ref('forlife_base.stock_warehouse_type_04', raise_if_not_found=False).id
        warehouse_type_id_ec = self.env['stock.warehouse.type'].sudo().search([('code', '=', 5)])
        warehouse_type_id_ec = warehouse_type_id_ec.id if warehouse_type_id_ec else 0
        s_location_pos = self.env.ref('forlife_stock.warehouse_for_pos', raise_if_not_found=False).id
        s_location_error = self.env.ref('forlife_stock.warehouse_error', raise_if_not_found=False).id
        s_location_sell_ecommerce = self.env.ref('forlife_stock.sell_ecommerce', raise_if_not_found=False).id
        location_id = self.env['stock.location'].sudo().search([('id', '=', self.location_id.id)])
        location_dest_id = self.env['stock.location'].sudo().search([('id', '=', self.location_dest_id.id)])
        warehouse_id = location_id.warehouse_id.whs_type.id
        warehouse_dest_id = location_dest_id.warehouse_id.whs_type.id
        s_location_type_id = location_id.stock_location_type_id.id
        s_location_dest_type_id = location_dest_id.stock_location_type_id.id
        if warehouse_id in [warehouse_type_id_tl, warehouse_type_id_fm,warehouse_type_id_ec] \
                and warehouse_dest_id in [warehouse_type_id_tl,warehouse_type_id_fm, warehouse_type_id_ec] \
                and s_location_type_id in [s_location_pos, s_location_error, s_location_sell_ecommerce] \
                and s_location_dest_type_id in [s_location_pos, s_location_error, s_location_sell_ecommerce]:
            if company.code == '1300':
                company_match = self.env['res.company'].sudo().search([('code', '=', '1400')])
                location_mapping = self.env['stock.location.mapping'].search([('location_id', '=', self.location_id.id)])
                location_dest_mapping = self.env['stock.location.mapping'].search([('location_id', '=', self.location_dest_id.id)])
                location = location_mapping.with_company(company_match).location_map_id.id
                location_dst = location_dest_mapping.with_company(company_match).location_map_id.id
            else:
                company_match = self.env['res.company'].sudo().search([('code', '=', '1300')])
                location_mapping = self.env['stock.location.mapping'].search([('location_map_id', '=', self.location_id.id)])
                location_dest_mapping = self.env['stock.location.mapping'].search([('location_map_id', '=', self.location_dest_id.id)])
                location = location_mapping.with_company(company_match).location_id.id
                location_dst = location_dest_mapping.with_company(company_match).location_id.id
            if (not location_mapping and self.location_id.id_deposit) or (not location_dest_mapping and self.location_dest_id.id_deposit):
                raise UserError(_(f"Vui lòng cấu hình liên kết cho 2 địa điểm này: Cấu hình -> Location Mapping!"))
            if location_mapping and location_dest_mapping:
                line = []
                for l in self.stock_transfer_line:
                    line.append((0, 0, {
                        'product_id': l.with_company(company_match).product_id.id,
                        'qty_plan': l.qty_plan,
                        'qty_out': l.qty_out,
                        'qty_in': l.qty_in,
                        'uom_id': l.uom_id.id
                    }))
                vals = {
                    'employee_id': self.employee_id.id,
                    'location_id': location,
                    'location_dest_id': location_dst,
                    'stock_transfer_line': line,
                    'company_id': company_match.id
                }
                res = self.env['stock.transfer'].with_company(company_match).sudo().create(vals)
                res.with_context(company_byside=company_match.id)._action_in_approve()
            return True
        return False
    from_company = fields.Many2one('res.company')
    to_company = fields.Many2one('res.company')