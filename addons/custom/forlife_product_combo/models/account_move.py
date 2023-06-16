from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')
    origin_invoice_id = fields.Many2one('account.move', string='Origin Invoice', readonly=True, check_company=True)

    def button_popup_increase_decrease_invoice(self):

        return {
            'name': 'Tăng/giảm hóa đơn',
            'domain': [],
            'res_model': 'wizard.increase.decrease.invoice',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'default_origin_invoice_id': self.id},
            'target': 'new',
        }
