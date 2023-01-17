from odoo import api, fields, models


class PartnerHistoryPointForLife(models.Model):
    _name = 'partner.history.point'

    _description = 'History of Customer purchase POS'

    point_order_type = fields.Selection([('new', 'Order New'), ('back_order', 'Back Order'),('reset_order', 'Reset Point'),('point compensate', 'Point Compensate')], string='Type')

    partner_id = fields.Many2one('res.partner')
    date_order = fields.Datetime('Date Order')
    points_fl_order = fields.Integer('Points Order')
    points_used = fields.Integer('Points Used')
    points_back = fields.Integer('Points Back')
    points_store = fields.Integer('Points Store')
    reason = fields.Text('Reason')
    store = fields.Selection([('forlife', 'For Life'), ('format', 'Format')])