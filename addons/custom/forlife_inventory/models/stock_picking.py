from odoo import api, fields, models
from datetime import date, datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        picking = super(StockPicking, self)._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type,
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
            location_mapping = self.env['stock.location.mapping'].sudo().search(
                [('location_id', '=', picking.location_dest_id.id)])
            if location_mapping:
                company = location_mapping.location_map_id.warehouse_id.company_id.id
                for line in picking.move_ids_without_package:
                    product = line.product_id
                    data.append((0, 0, {
                        'product_id': product.id,
                        'name': product.display_name,
                        'date': datetime.now(),
                        'product_uom': line.uom_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'quantity_done': line.quantity_done,
                    }))
                Picking.with_company(company).create({
                    'transfer_id': self.id,
                    'picking_type_id': location_mapping.location_map_id.warehouse_id.int_type_id.id,
                    'location_id': location_mapping.location_map_id.id,
                    'location_dest_id': location_mapping.location_map_id.id,
                    'move_ids_without_package': data,
                })

        return picking

    def create_move(self, company):
        move_vals = {
            'journal_id': self.pos_order_id.sale_journal.id,
            'date': self.pos_order_id.date_order,
            'ref': self.pos_order_id.name,
            'line_ids': [
                (0, 0, {
                    'name': self.pos_order_id.name,
                    'account_id': self.product_id.categ_id.property_account_income_categ_id.id,
                    'debit': order_cost,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': self.pos_order_id.name,
                    'account_id': self.product_id.categ_id.property_account_expense_categ_id.id,
                    'debit': 0.0,
                    'credit': order_cost,
                })
            ]
        }
        move = self.env['account.move'].with_company(company).create(move_vals)
        move.action_post()
        return move
