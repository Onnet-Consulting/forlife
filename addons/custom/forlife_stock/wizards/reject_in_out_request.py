from odoo import fields, models, api


class RejectImportExportRequest(models.TransientModel):
    _name = "reject.in.out.request"
    _description = "Reject Import Export Request"

    reject_reason = fields.Text(required=True)

    def action_reject(self):
        req_id = self._context.get('active_id')
        current_request = self.env['forlife.other.in.out.request'].search([('id', '=', req_id)], limit=1)
        if current_request:
            current_request.write({
                'status': 'reject',
                'reject_reason': self.reject_reason
            })
            return {
                'name': ('in.out.request.form'),
                'view_mode': 'form',
                'view_id': self.env.ref('forlife_stock.forlife_other_in_out_request_form').id,
                'res_model': 'forlife.other.in.out.request',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': current_request.id,
            }