from odoo import api, fields, models


class PartnerHistoryPointForLife(models.Model):
    _name = 'partner.history.point'

    _description = 'History of Customer purchase POS'
    _order = 'create_date desc'

    point_order_type = fields.Selection([('new', 'Order New'), ('back_order', 'Back Order'),('reset_order', 'Reset Point'),('point compensate', 'Point Compensate')], string='Type', readonly=False)

    partner_id = fields.Many2one('res.partner')
    date_order = fields.Datetime('Date Order', readonly=False)
    points_fl_order = fields.Integer('Points Order',readonly=False)
    points_used = fields.Integer('Points Used',readonly=False)
    points_back = fields.Integer('Points Back',readonly=False)
    points_store = fields.Integer('Points Store',readonly=False)
    reason = fields.Text('Reason',readonly=False)
    store = fields.Selection([('forlife', 'For Life'), ('format', 'Format')], readonly=False)
    pos_order_id = fields.Many2one('pos.order', readonly=True, string='POS Order')
    create_date = fields.Datetime(readonly=False)
