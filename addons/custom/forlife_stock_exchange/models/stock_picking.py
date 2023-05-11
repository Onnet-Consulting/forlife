from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    exchange_code = fields.Selection(related='picking_type_id.exchange_code')
    picking_outgoing_id = fields.Many2one('stock.picking', index=True)

    def view_outgoing_picking(self):
        return {
            'name': _('Forlife Stock Exchange'),
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.picking_outgoing_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'view_id': self.env.ref('forlife_stock.inherit_stock_picking_for_other_export_form_view').id
        }

    def _generate_outgoing_move(self, move_incoming_ids):
        """
        Generate outgoing move for incoming picking
        """
        move_outgoing_values = []
        for move in move_incoming_ids:
            bom = move.env[move.bom_model].browse(move.bom_id)
            move_outgoing_values += ([{
                'picking_id': self.id,
                'name': material.product_id.name,
                'product_id': material.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_qty': 1,
                'price_unit': material.total,
                'bom_model': material._name,
                'bom_id': material.id,
            } for material in bom.forlife_bom_material_ids] + [{
                'picking_id': self.id,
                'name': ingredients.product_id.name,
                'product_id': ingredients.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_qty': 1,
                'price_unit': ingredients.total,
                'bom_model': ingredients._name,
                'bom_id': ingredients.id,
            } for ingredients in bom.forlife_bom_ingredients_ids] + [{
                'picking_id': self.id,
                'name': expense.product_id.name,
                'product_id': expense.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_qty': 1,
                'price_unit': expense.rated_level,
                'bom_model': expense._name,
                'bom_id': expense.id,
            } for expense in bom.forlife_bom_service_cost_ids])
        return self.env['stock.move'].create(move_outgoing_values)

    def _generate_outgoing_picking(self):
        """
        Generate and validate outgoing picking for incoming picking
        """
        picking_outgoing_id = self.create({
            'reason_type_id': self.env.ref('forlife_stock_exchange.forlife_reason_type_outgoing_exchange').id,
            'picking_type_id': self.env.ref('forlife_stock_exchange.forlife_picking_type_outgoing_exchange').id,
            'location_id': self.location_dest_id.id or self.env.ref('forlife_stock_exchange.forlife_stock_location_exchange').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'other_export': True,
        })
        picking_outgoing_id._generate_outgoing_move(self.move_ids)
        picking_outgoing_id.action_confirm()
        picking_outgoing_id.action_assign()
        if picking_outgoing_id.state != 'assigned':
            raise ValidationError(_('The stock "%s" is not enough goods to export!' % picking_outgoing_id.location_id.name))
        picking_outgoing_id.button_validate()
        return picking_outgoing_id

    def action_confirm(self):
        if self.picking_type_id.exchange_code == 'incoming':
            bom_ids = {
                bom.product_id.id: bom
                for bom in self.env['forlife.production.finished.product'].sudo().search(
                    [('product_id', 'in', self.move_ids.mapped('product_id.id'))]
                )
            }
            for incoming_move in self.move_ids:
                if incoming_move.product_id.id not in bom_ids:
                    raise ValidationError(_('Cannot find BOM (product %s)!' % incoming_move.product_id.name))
                price_unit = incoming_move.price_unit or bom_ids[incoming_move.product_id.id].unit_price
                incoming_move.write({
                    'bom_model': bom_ids[incoming_move.product_id.id]._name,
                    'bom_id': bom_ids[incoming_move.product_id.id].id,
                    'price_unit': price_unit,
                    'product_uom_qty': bom_ids[incoming_move.product_id.id].produce_qty,
                    'amount_total': price_unit * bom_ids[incoming_move.product_id.id].produce_qty
                })
            picking_outgoing_id = self._generate_outgoing_picking()
            self.write({'picking_outgoing_id': picking_outgoing_id.id})
        return super(InheritStockPicking, self).action_confirm()

    def action_cancel(self):
        for rec in self:
            if rec.picking_outgoing_id:
                rec.picking_outgoing_id.action_cancel()
                rec.picking_outgoing_id.action_back_to_draft()
                rec.picking_outgoing_id.unlink()
        return super(InheritStockPicking, self).action_cancel()

    def action_back_to_draft(self):
        for rec in self:
            if rec.picking_outgoing_id:
                rec.picking_outgoing_id.action_cancel()
                rec.picking_outgoing_id.action_back_to_draft()
                rec.picking_outgoing_id.unlink()
        return super(InheritStockPicking, self).action_back_to_draft()
