from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    exchange_code = fields.Selection(related='picking_type_id.exchange_code')
    picking_outgoing_id = fields.Many2one('stock.picking', copy=False, index=True)

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
        reason_type_id = self.env.ref('forlife_stock_exchange.forlife_reason_type_outgoing_exchange').id
        for move in move_incoming_ids:
            bom = move.env[move.bom_model].browse(move.bom_id)
            move_outgoing_value = [{
                'picking_id': self.id,
                'name': material.product_id.name,
                'product_id': material.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_qty': move.product_uom_qty,
                'price_unit': material.product_id.standard_price,
                'amount_total': move.product_uom_qty * material.product_id.standard_price,
                'bom_model': material._name,
                'bom_id': material.id,
                'reason_type_id': reason_type_id,
            } for material in bom.forlife_bom_material_ids] + [{
                'picking_id': self.id,
                'name': ingredients.product_id.name,
                'product_id': ingredients.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_qty': move.product_uom_qty,
                'price_unit': ingredients.product_id.standard_price,
                'amount_total': move.product_uom_qty * ingredients.product_id.standard_price,
                'bom_model': ingredients._name,
                'bom_id': ingredients.id,
                'reason_type_id': reason_type_id,
            } for ingredients in bom.forlife_bom_ingredients_ids] + [{
                'picking_id': self.id,
                'name': expense.product_id.name,
                'product_id': expense.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_qty': move.product_uom_qty,
                'price_unit': expense.product_id.standard_price,
                'amount_total': move.product_uom_qty * expense.product_id.standard_price,
                'bom_model': expense._name,
                'bom_id': expense.id,
                'reason_type_id': reason_type_id,
            } for expense in bom.forlife_bom_service_cost_ids]
            if not move_outgoing_value:
                raise ValidationError(_('No materials found for product "%s"!', move.product_id.name))
            move_outgoing_values += move_outgoing_value
        return self.env['stock.move'].create(move_outgoing_values)

    def _generate_outgoing_picking(self):
        """
        Generate and validate outgoing picking for incoming picking
        """
        company = self.env.company
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing'), ('exchange_code', '=', 'outgoing'), ('company_id', '=', company.id)],
            limit=1
        )
        if not picking_type:
            raise ValidationError(_('Please configure the materials export operation type for company %s!', company.name))
        picking_outgoing_id = self.create({'location_id': self.location_dest_id.id, 'origin': self.name})
        picking_outgoing_id._generate_outgoing_move(self.move_ids)
        '''
        picking_outgoing_id.action_confirm()
        picking_outgoing_id.action_assign()
        if picking_outgoing_id.state != 'assigned':
            raise ValidationError(_('The stock "%s" dose not enough goods to export materials!', picking_outgoing_id.location_id.name))
        '''
        return picking_outgoing_id

    def button_validate(self):
        results = super(InheritStockPicking, self).button_validate()
        if self.picking_type_id.exchange_code == 'incoming' and self.state == 'done':
            self._update_forlife_production()
            bom_ids = {
                bom.product_id.id: bom
                for bom in self.env['forlife.production.finished.product'].sudo().search(
                    [('product_id', 'in', self.move_ids.mapped('product_id.id'))]
                )
            }
            for move_in in self.move_ids:
                if move_in.product_id.id not in bom_ids:
                    raise ValidationError(_('Cannot find BOM for product "%s"!', move_in.product_id.name))
                price_unit = move_in.price_unit or bom_ids[move_in.product_id.id].unit_price
                move_in.write({
                    'bom_model': bom_ids[move_in.product_id.id]._name,
                    'bom_id': bom_ids[move_in.product_id.id].id,
                    'price_unit': price_unit,
                    'amount_total': price_unit * move_in.product_uom_qty
                })
            picking_outgoing_id = self.with_context(exchange_code='outgoing')._generate_outgoing_picking()
            self = self.with_context(exchange_code='incoming')
            self.write({'picking_outgoing_id': picking_outgoing_id.id})
        return results

    def _update_forlife_production(self):
        for line in self.move_ids_without_package:
            if line.work_production:
                forlife_production = line.work_production.forlife_production_finished_product_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
                if not forlife_production:
                    continue
                forlife_production.write({
                    'forlife_production_stock_move_ids': [(4, line.id)],
                })

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

    @api.model
    def default_get(self, fields):
        results = super(InheritStockPicking, self).default_get(fields)
        exchange_code = self._context.get('exchange_code')
        if exchange_code == 'incoming':
            company = self.env.company
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming'), ('exchange_code', '=', 'incoming'), ('company_id', '=', company.id)],
                limit=1
            )
            if not picking_type:
                raise ValidationError(_('Please configure the finished product import operation type for company %s!', company.name))
            ref = self.env.ref
            results.update({
                'picking_type_id': picking_type.id,
                'location_id': ref('forlife_stock_exchange.forlife_location_incoming_exchange').id,
                'location_dest_id': None,
                'reason_type_id': ref('forlife_stock_exchange.forlife_reason_type_incoming_exchange').id,
                'other_import': True
            })
        elif exchange_code == 'outgoing':
            company = self.env.company
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing'), ('exchange_code', '=', 'outgoing'), ('company_id', '=', company.id)],
                limit=1
            )
            if not picking_type:
                raise ValidationError(_('Please configure the materials export operation type for company %s!', company.name))
            ref = self.env.ref
            results.update({
                'picking_type_id': picking_type.id,
                'location_dest_id': ref('forlife_stock_exchange.forlife_location_outgoing_exchange').id,
                'reason_type_id': ref('forlife_stock_exchange.forlife_reason_type_outgoing_exchange').id,
                'other_export': True
            })
        return results

