from odoo import fields, models, api


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_state_registration = fields.Boolean(string='State Registration', store=False)
    pos_order_line_id = fields.Many2one(comodel_name='pos.order.line', string='POS Order Line', index=True)