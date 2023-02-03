from odoo import api, fields, models,_

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_related_pos(self):
        return {
            'name': _('Pos Order'),
            'domain': [('id', 'in', self.pos_order_ids.ids)],
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
        }