from odoo import fields, models, api


class RejectAssetTransfer(models.TransientModel):
    _name = "reject.asset.transfer"
    _description = "Reject Asset Transfer"

    reject_reason = fields.Text(string='Lý do từ chối')

    def action_reject(self):
        req_id = self._context.get('active_id')
        current_request = self.env['hr.asset.transfer'].search([('id', '=', req_id)], limit=1)
        if current_request:
            current_request.write({
                'state': 'reject',
                'reject_reason': self.reject_reason
            })
            return {
                'name': ('hr.asset.transfer.form'),
                'view_mode': 'form',
                'view_id': self.env.ref('forlife_stock.hr_asset_transfer_form_view').id,
                'res_model': 'hr.asset.transfer',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': current_request.id,
            }