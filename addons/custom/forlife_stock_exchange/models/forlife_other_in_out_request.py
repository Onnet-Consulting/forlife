from odoo import models


class InheritForlifeOtherInOutRequest(models.Model):
    _inherit = 'forlife.other.in.out.request'

    def action_approve(self):
        result = super(InheritForlifeOtherInOutRequest, self).action_approve()
        ForlifeReasonType = self.env['forlife.reason.type']
        company = self.env.company
        reason_type_incoming_exchange_id = ForlifeReasonType.search([('code', '=', 'N01'), ('company_id', '=', company.id)], limit=1)
        # forlife_reason_type_incoming_exchange = self.env.ref('forlife_stock_exchange.forlife_reason_type_incoming_exchange')
        pickings = self.env['stock.picking'].sudo().search(
            [('other_import_export_request_id', 'in', [rec.id for rec in self if rec.type_other_id == reason_type_incoming_exchange_id])],
        )
        if pickings:
            picking_type_id = self.env['stock.picking.type'].sudo().search([('exchange_code', '=', 'incoming')], limit=1)
            if picking_type_id:
                pickings.write({'picking_type_id': picking_type_id.id})
        return result

    def action_other_import_export(self):
        ref = self.env.ref
        ForlifeReasonType = self.env['forlife.reason.type']
        company = self.env.company
        reason_type_incoming_exchange_id = ForlifeReasonType.search(
            [('code', '=', 'N01'), ('company_id', '=', company.id)], limit=1)
        if self.type_other_id == reason_type_incoming_exchange_id:
            picking_id = self.env['stock.picking'].sudo().search(
                [('other_import_export_request_id', '=', self.id), ('picking_type_id.exchange_code', '=', 'incoming')],
                limit=1
            ).id
            if not picking_id:
                return None
            action = ref('forlife_stock_exchange.action_forlife_stock_exchange')
            result = {
                'name': action.name,
                'res_model': action.res_model,
                'context': action.context,
                'view_mode': 'form',
                'res_id': picking_id,
                'type': 'ir.actions.act_window',
                'view_id': ref('forlife_stock.inherit_stock_picking_for_other_export_form_view').id,
            }
        else:
            result = super(InheritForlifeOtherInOutRequest, self).action_other_import_export()
        return result
