from odoo import fields, models, api


class ConfirmContinueValidatePicking(models.TransientModel):
    _name = "confirm.continue.validate.picking"
    _description = "Confirm Continue Validate Picking"

    message = fields.Text('Cảnh báo')

    def action_continue(self):
        picking_ids = self._context.get('picking_ids')
        for picking_id in self.env['stock.picking'].browse(picking_ids):
            res = picking_id.with_context(check_date_done=0).button_validate()
            if isinstance(res, dict):
                return res
