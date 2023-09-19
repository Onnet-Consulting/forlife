from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import ValidationError


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    def create_import_export_other(self, vals, type_picking):
        company = self.env['res.company'].sudo().search([('code', '=', '1300')])
        if self.inventory_id.company_id.code == '1400':
            if type_picking == 'import':
                l_id = self.env['stock.location'].sudo().search([('id','=',vals['location_dest_id'])])
                location_mapping = self.env['stock.location.mapping'].sudo().search([('location_map_id', '=', l_id.id)])
                #if not location_mapping:
                #    raise UserError(_(f"Vui lòng cấu hình liên kết cho địa điểm {l_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
            else:
                l_id = self.env['stock.location'].sudo().search([('id', '=', vals['location_id'])])
                location_mapping = self.env['stock.location.mapping'].sudo().search([('location_map_id', '=', vals['location_id'])])
                #if not location_mapping:
                #    raise UserError(_(f"Vui lòng cấu hình liên kết cho địa điểm {l_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
            if location_mapping:
                location_id = location_mapping.location_id
                type_id = location_id.with_company(company).warehouse_id.int_type_id.id
                product = self.env['product.product'].search([('id', '=', vals['product_id'])])
                ReasonType = self.env['forlife.reason.type'].sudo()
                if type_picking == 'import':
                    loc = self.env['stock.location'].sudo().search([('code', '=', 'N0202'), ('company_id', '=', company.id)], limit=1)
                    if not loc:
                        raise ValidationError(_('Không tìm thấy lí do "Nhập cân đối tồn kho - kiểm kê định kì mã N0202 ở công ty sản xuất"'))
                    picking = self.env['stock.picking'].with_company(company).sudo().create({
                        'reason_type_id': ReasonType.search([('code', '=', 'N02'), ('company_id', '=', company.id)], limit=1).id,
                        'picking_type_id': type_id,
                        'location_id': loc.id,
                        'location_dest_id': location_id.id,
                        'other_import': True,
                        'is_generate_auto_company':True,
                        'move_ids_without_package': [(0, 0, {
                            'product_id': product.id,
                            'location_id': loc.id,
                            'location_dest_id': location_id.id,
                            'name': vals['name'],
                            'product_uom': vals['product_uom'],
                            'product_uom_qty': vals['product_uom_qty'],
                            'quantity_done': vals['product_uom_qty'],
                            'amount_total': vals['product_uom_qty'] * product.standard_price,
                            'company_id': company.id
                        })],
                    })
                else:
                    loc_dest = self.env['stock.location'].sudo().search([('code', '=', 'X0202'), ('company_id', '=', company.id)], limit=1)
                    if not loc_dest:
                        raise ValidationError(_('Không tìm thấy lí do "Xuất cân đối tồn kho - kiểm kê định kì mã X0202 ở công ty sản xuất"'))
                    picking = self.env['stock.picking'].with_company(company).sudo().create({
                        'reason_type_id': ReasonType.search([('code', '=', 'X02'), ('company_id', '=', company.id)], limit=1).id,
                        'picking_type_id': type_id,
                        'location_id': location_id.id,
                        'location_dest_id': loc_dest.id,
                        'other_export': True,
                        'is_generate_auto_company':True,
                        'move_ids_without_package': [(0, 0, {
                            'product_id': product.id,
                            'location_id': location_id.id,
                            'location_dest_id': loc_dest.id,
                            'name': vals['name'],
                            'product_uom': vals['product_uom'],
                            'product_uom_qty': vals['product_uom_qty'],
                            'quantity_done': vals['product_uom_qty'],
                            'amount_total': vals['product_uom_qty'] * product.standard_price,
                            'company_id': company.id
                        })],
                    })
                picking.with_context(endloop=True).button_validate()
                picking.date_done = self.inventory_id.date
                return picking
        return True
