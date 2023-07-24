from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_type = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], string='Type')
    origin_invoice_id = fields.Many2one('account.move', string='Origin Invoice', readonly=True, check_company=True)
    increase_decrease_inv_count = fields.Integer(compute="_compute_increase_decrease_inv_count", string='Increase/decrease invoice count')

    def _compute_increase_decrease_inv_count(self):
        for move in self:
            move.increase_decrease_inv_count = self.search_count([('origin_invoice_id', '=', move.id)])

    def action_view_increase_decrease_invoice(self):
        self.ensure_one()
        invoices = self.search([('origin_invoice_id', 'in', self.ids)])
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        if len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = invoices.id
        else:
            result['domain'] = [('id', 'in', invoices.ids)]
        return result

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

    def _get_unbalanced_moves(self, container):
        if self.origin_invoice_id:
            return []
        else:
            return super(AccountMove, self)._get_unbalanced_moves(container)