from odoo import api, fields, models, _


class PointsPromotion(models.Model):
    _name = 'points.promotion'
    _description = 'Points Promotion'

    name = fields.Char('Program Name', required=True)
    branch_id = fields.Char(string='Branch', required=True)  # fixme Many2one đến model branch
    store_ids = fields.Char(string='Stores', required=True)  # fixme Many2many model store định nghĩa trong module forlife_point_of_sale
    from_date = fields.Datetime('From Date', required=True)
    to_date = fields.Datetime('To Date', required=True)
    first_order = fields.Integer('First Order')
    payment_method_ids = fields.Many2many('pos.payment.method', string='Payment Method', required=True)
    point_expiration = fields.Integer('Point Expiration')
    point_partner_id = fields.Many2one('res.partner', string='Point Partner', required=True)
    point_account_id = fields.Many2one('account.account', string='Point Account', required=True)
    point_use_account_id = fields.Many2one('account.account', string='Point Use Account', required=True)
    point_consumption_account_id = fields.Many2one('account.account', string='Point Consumption Account', required=True)
    point_consumption_tax_account_id = fields.Many2one('account.account', string='Point Consumption Tax Account', required=True)
    account_journal_id = fields.Many2one('account.journal', string='Account Journal', required=True)
    state = fields.Selection([('new', _('New')), ('in_progress', _('In Progress')), ('finish', _('Finish'))], string='State', default='new')
    value_conversion = fields.Integer('Value Conversion', required=True)
    point_addition = fields.Integer('Point Addition', required=True)
    line_ids = fields.One2many('points.promotion.line', inverse_name='points_promotion_id', string='Lines')

    def btn_apply(self):
        self.state = 'in_progress'

    def btn_finish(self):
        self.state = 'finish'

    def btn_events(self):
        pass

    def btn_product_point_consumption(self):
        pass

    def btn_update(self):
        pass
