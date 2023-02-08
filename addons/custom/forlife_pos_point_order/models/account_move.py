from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    point_order_type = fields.Selection([('new', 'Order New'), ('back_order', 'Back Order'), ('reset_order', 'Reset Point'), ('point compensate', 'Point Compensate')], string='Type', readonly=True)

    def action_related_pos(self):
        return {
            'name': _('Pos Order'),
            'domain': [('id', 'in', self.pos_order_ids.ids)],
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
        }
