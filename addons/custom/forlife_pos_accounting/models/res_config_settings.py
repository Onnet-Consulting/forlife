from odoo import models, fields


class InheritResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_default_pos_defective_goods_id = fields.Many2one(
        string='Defective Goods',
        related='company_id.product_default_pos_defective_goods_id',
        readonly=False
    )

    product_default_pos_handle_discount_id = fields.Many2one(
        string='Handel Discount',
        related='company_id.product_default_pos_handle_discount_id',
        readonly=False
    )

    is_promotional_accounting_without_state_registration = fields.Boolean(
        related='company_id.is_promotional_accounting_without_state_registration',
        string='Is Promotional Accounting Without State Registration',
        readonly=False
    )
