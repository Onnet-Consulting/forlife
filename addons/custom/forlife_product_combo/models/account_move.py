from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'


    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')

    def button_increase_decrease_invoice(self, default=None):

        self.ensure_one()
        default = dict(default or {})
        default['invoice_type'] = 'increase'
        move_copy_id = self.copy(default)

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'res_id': move_copy_id.id,
        }


    @api.onchange('invoice_type')
    def onchange_view_invoice_type(self):
        for rec in self:
            rec.invoice_line_ids = [(5, 0)]
            if rec.line_ids:
                for line in rec.line_ids:
                    id  = line.id
                    line.unlink()
            # if rec.partner_id:
            #     receiving_warehouse = []
            #     invoice_line_ids = rec.invoice_line_ids.filtered(lambda line: line.product_id)
            #     rec.is_check_cost_view = True

                # unlink()