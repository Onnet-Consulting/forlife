from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    other_picking_type_id = fields.Many2one('stock.picking.type', string="Kiểu giao nhận xuất/nhập khác")
    other_location_id = fields.Many2one('stock.location', string="Lý do xuất/nhập khác mặc định")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self._context.get('endloop'):
            return res
        for picking in self:
            if picking.state == 'done' and \
                    ((picking.purchase_id and picking.purchase_id.is_return) or \
                     (picking.move_ids and picking.move_ids[0]._is_purchase_return())):
                picking.create_return_valuation_npl()
        return res

    def _get_picking_info_return(self, po):
        incoming_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.env.company.id)], limit=1)
        picking_type_id = incoming_type_id
        if po and po.picking_type_id:
            # if not po.picking_type_id.other_picking_type_id:
            #     raise ValidationError("Vui lòng thiết lập 'Kiểu giao nhận xuất/nhập khác' tại Kiểu giao nhận tương ứng.")
            if po.picking_type_id.other_picking_type_id:
                picking_type_id = po.picking_type_id.other_picking_type_id
            elif po.picking_type_id.return_picking_type_id:
                picking_type_id = po.picking_type_id.return_picking_type_id

        production_order = self.env['production.order'].search([('product_id', 'in', self.move_ids.product_id.ids), ('type', '=', 'normal')], limit=1)
        if (po and po.is_return and po.order_line_production_order) or (po and production_order):
            location_id = self.env['stock.location'].search([('code', '=', 'N0701'), ('company_id', '=', self.env.company.id)], limit=1)
            if not location_id:
                raise ValidationError("Hiện tại sản phẩm xuất trả có sản phẩm đính kèm NPL. Nhưng trong cấu hình Lý Do Nhập Khác chưa định nghĩa loại lý do có Mã = N0701. Yêu cầu liên hệ admin để xử lý")
        elif picking_type_id.other_location_id:
            location_id = picking_type_id.other_location_id
        else:
            location_id = self.env.ref('forlife_stock.import_production_order')

        return picking_type_id, location_id

    def create_return_picking_npl(self, po, record, lines_npl):
        picking_type_id, location_id = self._get_picking_info_return(po)

        vals = {
            "is_locked": True,
            "immediate_transfer": False,
            'reason_type_id': self.env.ref('forlife_stock.reason_type_7').id,
            'location_id': location_id.id,
            'location_dest_id': record.location_id.id,
            'scheduled_date': fields.datetime.now(),
            'origin': po.name + " nhập trả NPL" if po else record.name + " nhập trả NPL",
            'state': 'assigned',
            'picking_type_id': picking_type_id.id,
            'move_ids_without_package': lines_npl,
            'other_import': True
        }
        picking_npl = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(vals)
        ctx = picking_npl._context.copy()
        ctx.update({'extend_account_npl': True})
        picking_npl.with_context(ctx).button_validate()
        record.write({'picking_xk_id': picking_npl.id})
        return picking_npl

    def create_return_valuation_npl(self):
        lines_npl = []
        picking_type_id, npl_location_id = self._get_picking_info_return(self.purchase_id)
        reason_type_id = self.env.ref('forlife_stock.reason_type_7').id
        if not self.purchase_id.is_return:
            for move in self.move_ids:
                for material_line_id in move.purchase_line_id.purchase_order_line_material_line_ids.filtered(lambda x: not x.type_cost_product):
                    data = self._prepare_material_lines(move, material_line_id, npl_location_id, reason_type_id, move.purchase_line_id)
                    lines_npl.append(data)
        else:
            for move in self.move_ids:
                for material_line_id in move.purchase_line_id.origin_po_line_id.purchase_order_line_material_line_ids.filtered(lambda x: not x.type_cost_product):
                    data = self._prepare_material_lines(move, material_line_id, npl_location_id, reason_type_id, move.purchase_line_id.origin_po_line_id)
                    lines_npl.append(data)

        if lines_npl:
            self.create_return_picking_npl(self.purchase_id, self, lines_npl)
        return True

    def _prepare_material_lines(self, move, material_line_id, npl_location_id, reason_type_id, purchase_line_id):
        product_plan_qty = move.quantity_done * (material_line_id.product_qty / purchase_line_id.product_qty)
        return (0, 0, {
            'product_id': material_line_id.product_id.id,
            'product_uom': material_line_id.uom.id,
            'price_unit': material_line_id.production_line_price_unit,
            'location_id': npl_location_id.id,
            'location_dest_id': self.location_id.id,
            'product_uom_qty': product_plan_qty,
            'quantity_done': product_plan_qty,
            'amount_total': material_line_id.production_line_price_unit * product_plan_qty,
            'reason_type_id': reason_type_id,
            'reason_id': npl_location_id.id,
            'include_move_id': move.id
        })