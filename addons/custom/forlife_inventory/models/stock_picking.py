from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    from_company = fields.Many2one('res.company')
    to_company = fields.Many2one('res.company')
    from_po_give = fields.Boolean(default=False)

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        location_enter_inventory_balance_auto = self.env['stock.location'].sudo().search([('code', '=', 'X701')], limit=1)
        location_dest_check_id = self.env['stock.location'].sudo().search([('code', '=', 'X0202')], limit=1)
        if 'endloop' in self._context and self._context.get('endloop'):
            return res
        if self.company_id.code == '1300':
            reason_type_5 = self.env['forlife.reason.type'].search([('code', '=', 'N02'), ('company_id', '=', self.company_id.id)])
            reason_type_4 = self.env['forlife.reason.type'].search([('code', '=', 'X02'), ('company_id', '=', self.company_id.id)])
            ec_warehouse_id = self.env.ref('forlife_stock.sell_ecommerce', raise_if_not_found=False).id
            if self.sale_id.source_record and self.picking_type_code == 'outgoing' and not self.x_is_check_return \
                    and self.location_id.stock_location_type_id.id == ec_warehouse_id:
                self.create_other_give(type_create='export')
            if self.sale_id.source_record and self.picking_type_code == 'incoming' and self.x_is_check_return and self.location_dest_id.stock_location_type_id.id == ec_warehouse_id:
                self.create_other_give(type_create='import')
            po = self.purchase_id
            product_is_voucher = self.move_line_ids_without_package.filtered(lambda x: x.product_id.voucher)
            product_not_voucher = self.move_line_ids_without_package.filtered(lambda x: not x.product_id.voucher)
            if po and not po.is_inter_company and po.type_po_cost == 'cost' and po.location_id.id_deposit:
                if product_is_voucher and not product_not_voucher:
                    self.create_other_give(type_create='from_po')
            if self.reason_type_id.id == reason_type_5.id and self.location_id.id == location_enter_inventory_balance_auto.id and self.location_dest_id.id_deposit:
                if product_is_voucher and not product_not_voucher:
                    self.create_check_inventory(type_create='import')
            if self.reason_type_id.id == reason_type_4.id and self.location_dest_id.id == location_dest_check_id.id and self.location_id.id_deposit:
                if product_is_voucher and not product_not_voucher:
                    self.create_check_inventory(type_create='export')
        return res

    def create_check_inventory(self, type_create):
        if type_create == 'import':
            location_mapping = self.env['stock.location.mapping'].sudo().search([('location_id', '=', self.location_dest_id.id)])
            company_id = location_mapping.location_map_id.company_id.id
            location_id = self.env['stock.location'].sudo().search([('code', '=', 'X701'),('company_id','=',company_id)])
            if not location_id:
                raise UserError(_(f"Không tìm thấy địa điểm {self.location_id.name_get()[0][1]} ở công ty bán lẻ"))
            location_dest_id = location_mapping.location_map_id.id
            reason_type_id = self.env['forlife.reason.type'].sudo().search([('code', '=', 'N02'), ('company_id', '=', company_id)])
            if not location_mapping:
                raise UserError(_(f"Vui lòng cấu hình liên kết cho địa điểm {self.location_dest_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
        else:
            location_mapping = self.env['stock.location.mapping'].sudo().search([('location_id', '=', self.location_id.id)])
            company_id = location_mapping.location_map_id.company_id.id
            location_id = location_mapping.location_map_id.id
            location_dest_id = self.env['stock.location'].sudo().search([('code', '=', 'X0202'),('company_id','=', company_id)])
            if not location_dest_id:
                raise UserError(_(f"Không tìm thấy địa điểm {self.location_dest_id.name_get()[0][1]} ở công ty bán lẻ"))
            reason_type_id = self.env['forlife.reason.type'].sudo().search([('code', '=', 'X02'), ('company_id', '=', company_id)])
            if not location_mapping:
                raise UserError(_(f"Vui lòng cấu hình liên kết cho địa điểm {self.location_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
        data = []
        for line in self.move_line_ids_without_package:
            product = line.product_id
            data.append((0, 0, {
                'product_id': product.id,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'name': product.display_name,
                'date': datetime.now(),
                'product_uom': line.product_uom_id.id,
                'product_uom_qty': line.qty_done,
                'quantity_done': line.qty_done,
                'amount_total': 0,
                'company_id': company_id,
            }))
        other = self.env['stock.picking'].with_company(company_id).create({
            'reason_type_id': reason_type_id.id,
            'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'other_import': True if type_create == 'import' else False,
            'other_export': True if type_create == 'export' else False,
            'move_ids_without_package': data,
        })
        other = self.validate_picking_give_voucher(other=other, company_id=company_id)
        return other

    def create_other_give(self, type_create):
        if type_create == 'import' or type_create == 'from_po':
            location_mapping = self.env['stock.location.mapping'].sudo().search([('location_id', '=', self.location_dest_id.id)])
            if not location_mapping:
                raise UserError(_(f"Vui lòng cấu hình liên kết cho địa điểm {self.location_dest_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
            comId = location_mapping.location_map_id.company_id.id
            location_id = self.env['stock.location'].sudo().search([('code','=','N0601'), ('company_id','=',comId)], limit=1).id
            location_dest_id = location_mapping.location_map_id.id
            reason_type_id = self.env['forlife.reason.type'].sudo().search([('code', '=', 'N05'), ('company_id', '=', comId)])
        else:
            location_mapping = self.env['stock.location.mapping'].sudo().search([('location_id', '=', self.location_id.id)])
            comId = location_mapping.location_map_id.company_id.id
            if not location_mapping:
                raise UserError(_(f"Vui lòng cấu hình liên kết cho địa điểm {self.location_id.name_get()[0][1]} Cấu hình -> Location Mapping!"))
            location_id = location_mapping.location_map_id.id
            location_dest_id = self.env['stock.location'].sudo().search([('code','=','X1101'), ('company_id','=',comId)], limit=1).id
            reason_type_id = self.env['forlife.reason.type'].sudo().search([('code', '=', 'X11'), ('company_id', '=', comId)])
        data = []
        company_id = location_mapping.location_map_id.company_id.id
        for line in self.move_line_ids_without_package:
            product = line.product_id
            data.append((0, 0, {
                'product_id': product.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'name': product.display_name,
                'date': datetime.now(),
                'product_uom': line.product_uom_id.id,
                'product_uom_qty': line.qty_done,
                'quantity_done': line.qty_done,
                'amount_total': 0,
                'company_id': company_id,
            }))
        # if self.sale_id.nhanh_id and self.company_id.code == '1300':
        other = self.env['stock.picking'].with_company(location_mapping.location_map_id.company_id).create({
            'reason_type_id': reason_type_id,
            'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
            'location_id': location_id,
            'from_po_give': True if type_create == 'from_po' else False,
            'location_dest_id': location_dest_id,
            'other_import': True if type_create == 'import' else False,
            'other_export': True if type_create == 'export' else False,
            'move_ids_without_package': data,
        })
        if type_create == 'from_po':
            other = self.validate_picking_give_voucher(other=other, company_id=company_id)
            return other
        other.with_context(endloop=True).button_validate()
        return other

    def validate_picking_give_voucher(self, other, company_id):
        other.action_confirm()
        if self.move_line_ids_without_package:
            for i in range(0, len(self.move_line_ids_without_package)):
                line = self.move_line_ids_without_package[i]
                lot = self.env['stock.lot'].with_company(company_id).create({
                    'name': line.lot_name,
                    'product_id': line.product_id.id,
                    'company_id': company_id
                })
                other.move_line_ids_without_package[i].write({
                    'lot_id': lot.id,
                    'lot_name': lot.name
                })
            other.with_context(endloop=True).button_validate()
            return other

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
                    if location_mapping and location_mapping.location_id.id_deposit and location_mapping.location_id.account_stock_give:
                        company = location_mapping.location_id.warehouse_id.company_id.id
                        location_id = self.env['stock.location'].sudo().search([('code', '=', 'N0501'), ('company_id', '=', company)])
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
                            'reason_type_id': self.env['forlife.reason.type'].sudo().search([('code','=','N05'), ('company_id','=',company)]),
                            'picking_type_id': location_mapping.location_id.warehouse_id.int_type_id.id,
                            'location_id': location_id.id,
                            'location_dest_id': location_mapping.location_id.id,
                            'other_import': True,
                            'move_ids_without_package': data,
                        })
                        pickking_ortherimport.button_validate()
        return pickings
