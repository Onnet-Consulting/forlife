from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round


class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    exchange_code = fields.Selection(related='picking_type_id.exchange_code')
    picking_outgoing_id = fields.Many2one('stock.picking', copy=False, index=True)
    location_export_id = fields.Many2one(
        comodel_name='stock.location', string='Location Export', index=True, domain=[('usage', '=', 'internal')]
    )

    @api.onchange('reason_type_id')
    def _onchange_reason_location_product(self):
        if self.reason_type_id:
            if self._context.get('exchange_code') == 'incoming':
                return {
                    'domain': {
                        'location_id': [('reason_type_id', '=', self.reason_type_id.id)]
                    }
                }

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

    def _generate_outgoing_move(self, picking, move_incoming_ids):
        """
        Generate outgoing move for incoming picking
        """
        move_outgoing_values = []
        reason_export_id = picking.location_id.reason_export_material_id
        if not reason_export_id:
            raise ValidationError(_("Please configure reason export material of reason %s." % picking.location_id.name))
        reason_type_id = self.env['forlife.reason.type'].browse(picking.location_id.reason_type_id.id)
        if not reason_type_id:
            raise ValidationError(_("Please configure reason type export material of reason %s." % picking.location_id.name))

        for move in move_incoming_ids:
            bom = move.env[move.bom_model].browse(move.bom_id)
            product_qty_prodution_remaining = self.env['quantity.production.order'].search([('location_id', '=', self.location_id.id), ('production_id.code', '=', move.work_production.code)])
            material_ids = bom.forlife_bom_material_ids.filtered(lambda x: x.product_id.detailed_type == 'product' and not x.product_backup_id)
            material_backup_ids = bom.forlife_bom_material_ids.filtered(lambda x: x.product_id.detailed_type == 'product' and x.product_backup_id)
            if not material_ids:
                raise ValidationError(_("BOM của sản phẩm '%s' hiện tại đang không có sản phẩm lưu kho, vui lòng kiểm tra lại!" %  move.product_id.display_name))
            for material in material_ids:
                move_outgoing_value = self.validate_product_backup(move, material, material_backup_ids, product_qty_prodution_remaining, reason_export_id, reason_type_id)
                if not move_outgoing_value:
                    raise ValidationError(_('No materials found for product "%s"!', move.product_id.name))
                for move_value in move_outgoing_value:
                    move_value.update({
                        'work_production': move.work_production.id,
                        'occasion_code_id': move.occasion_code_id.id,
                        'account_analytic_id': move.account_analytic_id.id,
                    })
                move_outgoing_values += move_outgoing_value
        return self.env['stock.move'].create(move_outgoing_values)

    def validate_product_backup(self, move, material, material_backup_ids, product_qty_prodution_remaining, reason_export_id, reason_type_id):
        product_prodution_quantity = product_qty_prodution_remaining.filtered(lambda x: x.product_id.id == material.product_id.id)
        product_qty = sum(product_prodution_quantity.mapped('quantity'))
        m_total = material.conversion_coefficient * material.rated_level * (1+material.loss/100)
        material_total = float_round(m_total, precision_rounding=material.production_uom_id.rounding)
        product_uom_qty = float_round(move.product_uom_qty * material_total, precision_rounding=material.production_uom_id.rounding)
        move_outgoing_value = []
        qty_remain = product_uom_qty
        if product_qty >= product_uom_qty:
            val = self.prepare_data_stock_move_material(material.product_id, reason_export_id, product_uom_qty, material, reason_type_id)
            move_outgoing_value.append(val)
            return move_outgoing_value

        if product_qty:
            qty_need = float_round(product_qty, precision_rounding=material.production_uom_id.rounding)
            val = self.prepare_data_stock_move_material(material.product_id, reason_export_id, qty_need, material, reason_type_id)
            move_outgoing_value.append(val)
            qty_remain = float_round(product_uom_qty - qty_need, precision_rounding=material.production_uom_id.rounding)

        if qty_remain:
            # Check sản phẩm thay thế Level 1
            material_backup_01 = material_backup_ids.filtered(lambda x: x.product_backup_id.id == material.product_id.id)
            if not material_backup_01:
                raise ValidationError(_('Sản phẩm "%s" không đủ tồn kho!', material.product_id.name))
            else:
                product_backup_01_prodution_quantity = product_qty_prodution_remaining.filtered(lambda x: x.product_id.id == material_backup_01.product_id.id)
                material_backup_01_qty = sum(product_backup_01_prodution_quantity.mapped('quantity'))
                if material_backup_01_qty >= qty_remain:
                    qty_need = float_round(qty_remain, precision_rounding=material_backup_01.production_uom_id.rounding)
                    val = self.prepare_data_stock_move_material(material_backup_01.product_id, reason_export_id, qty_need, material_backup_01, reason_type_id)
                    move_outgoing_value.append(val)
                    return move_outgoing_value

                if material_backup_01_qty:
                    qty_need = float_round(material_backup_01_qty, precision_rounding=material_backup_01.production_uom_id.rounding)
                    val = self.prepare_data_stock_move_material(material_backup_01.product_id, reason_export_id, qty_need, material_backup_01, reason_type_id)
                    move_outgoing_value.append(val)
                    qty_remain = float_round(qty_remain - qty_need, precision_rounding=material_backup_01.production_uom_id.rounding)

                if qty_remain:
                    # Check sản phẩm thay thế Level 2
                    material_backup_02 = material_backup_ids.filtered(lambda x: x.product_backup_id.id == material_backup_01.product_id.id)
                    if not material_backup_02:
                        raise ValidationError(_('Sản phẩm "%s" không đủ tồn kho!', material.product_id.name))
                    else:
                        product_backup_02_prodution_quantity = product_qty_prodution_remaining.filtered(lambda x: x.product_id.id == material_backup_02.product_id.id)
                        material_backup_02_qty = sum(product_backup_02_prodution_quantity.mapped('quantity'))
                        if material_backup_02_qty >= qty_remain:
                            val = self.prepare_data_stock_move_material(material_backup_02.product_id, reason_export_id, qty_remain, material_backup_02, reason_type_id)
                            move_outgoing_value.append(val)
                        else:
                            raise ValidationError(_('Sản phẩm "%s" không đủ tồn kho!', material.product_id.name))

        return move_outgoing_value

    def prepare_data_stock_move_material(self, product_id, reason_export_id, product_uom_qty, material, reason_type_id):
        return {
            'picking_id': self.id,
            'name': product_id.name,
            'product_id': product_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': reason_export_id.id,
            'product_uom_qty': product_uom_qty,
            'price_unit': product_id.standard_price,
            'amount_total': product_uom_qty * product_id.standard_price,
            'bom_model': material._name,
            'bom_id': material.id,
            'reason_type_id': reason_type_id.id,
        }


    def _generate_outgoing_picking(self):
        """
        Generate and validate outgoing picking for incoming picking
        """
        picking = self
        picking_outgoing_id = self.create({'location_id': self.location_export_id.id, 'origin': self.name})
        picking_outgoing_id._generate_outgoing_move(picking, self.move_ids)
        picking_outgoing_id.action_confirm()
        picking_outgoing_id.action_assign()
        materials_not_enough = '\n\t- '.join([
            sm.product_id.name if not sm.product_id.barcode else f'[{sm.product_id.barcode}] {sm.product_id.name}'
            for sm in picking_outgoing_id.move_ids_without_package if sm.state != 'assigned'
        ])
        if materials_not_enough:
            raise ValidationError(_(
                'The stock "%s" dose not enough goods to export materials:\n\t- %s',
                picking_outgoing_id.location_id.complete_name,
                materials_not_enough
            ))
        # picking_outgoing_id.button_validate()
        return picking_outgoing_id

    def button_validate(self):
        if self.picking_type_id.exchange_code == 'incoming':
            for move_in in self.move_ids:
                bom = move_in.work_production.forlife_production_finished_product_ids.filtered(lambda b: b.product_id.id == move_in.product_id.id)
                if len(bom) != 1:
                    raise ValidationError(
                        not bom and _('Cannot find BOM for product "%s"!', move_in.product_id.name)
                        or _('There are too many BOM for product "%s"!', move_in.product_id.name)
                    )
                bom.update_price()
                price_unit = bom.unit_price or move_in.price_unit
                move_in.write({
                    'bom_model': bom._name,
                    'bom_id': bom.id,
                    'price_unit': price_unit,
                    'amount_total': price_unit * move_in.product_uom_qty
                })
        res = super(InheritStockPicking, self).button_validate()
        if self.picking_type_id.exchange_code == 'incoming' and self.state == 'done':
            self._update_forlife_production()
            for move_in in self.move_ids:
                bom = move_in.work_production.forlife_production_finished_product_ids.filtered(lambda b: b.product_id.id == move_in.product_id.id)
                if len(bom) != 1:
                    raise ValidationError(
                        not bom and _('Cannot find BOM for product "%s"!', move_in.product_id.name)
                        or _('There are too many BOM for product "%s"!', move_in.product_id.name)
                    )
                bom.update_price()
                price_unit = bom.unit_price or move_in.price_unit
                move_in.write({
                    'bom_model': bom._name,
                    'bom_id': bom.id,
                    'price_unit': price_unit,
                    'amount_total': price_unit * move_in.product_uom_qty
                })

            # K tạo phiếu xuất NVL với trường hợp xuất thừa
            if self.location_id.code != 'N0103':
                picking_outgoing_id = self.with_context(exchange_code='outgoing')._generate_outgoing_picking()
                self = self.with_context(exchange_code='incoming')
                self.write({'picking_outgoing_id': picking_outgoing_id.id})

        return res

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
        StockLocation = self.env['stock.location']
        ForlifeReasonType = self.env['forlife.reason.type']
        company = self.env.company
        if exchange_code == 'incoming':
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('exchange_code', '=', 'incoming'), ('company_id', '=', company.id)], limit=1)
            if not picking_type:
                raise ValidationError(_('Please configure the finished product import operation type for company %s!', company.name))
            location_id = StockLocation.search([('code', '=', 'N0101'), ('company_id', '=', company.id)], limit=1)
            if not location_id:
                raise ValidationError(_('Please configure reason finished product import operation for company %s!' % company.name))
            reason_type_id = ForlifeReasonType.search([('code', '=', 'N01'), ('company_id', '=', company.id)], limit=1)
            if not reason_type_id:
                raise ValidationError(_('Please configure reason type incoming for company %s.' % company.name))

            results.update({
                'picking_type_id': picking_type.id,
                'location_id': location_id.id,
                'location_dest_id': None,
                'reason_type_id': reason_type_id.id,
                'other_import': True
            })
        elif exchange_code == 'outgoing':
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('exchange_code', '=', 'outgoing'), ('company_id', '=', company.id)], limit=1)
            if not picking_type:
                raise ValidationError(_('Please configure the materials export operation type for company %s!', company.name))

            location_dest_id = self.location_id.reason_export_material_id
            if not location_dest_id:
                location_dest_id = StockLocation.search([('code', '=', 'X1001'), ('company_id', '=', company.id)], limit=1)
                if not location_dest_id:
                    raise ValidationError(_('Vui lòng cấu hình "Lý do xuất NVL tương ứng" cho "%s"!' % self.location_id.name))

            reason_type_id = location_dest_id.reason_type_id
            if not reason_type_id:
                reason_type_id = ForlifeReasonType.search([('code', '=', 'X10'), ('company_id', '=', company.id)], limit=1)
                if not reason_type_id:
                    raise ValidationError(_('Vui lòng cấu hình "Loại lý do" cho "%s"!' % location_dest_id.name))

            results.update({
                'picking_type_id': picking_type.id,
                'location_dest_id': location_dest_id.id,
                'reason_type_id': reason_type_id.id or False,
                'other_export': True
            })
        return results

