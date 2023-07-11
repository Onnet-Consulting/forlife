from odoo import models, fields


class InheritResCompany(models.Model):
    _inherit = 'res.company'

    product_default_pos_defective_goods_id = fields.Many2one(
        comodel_name='product.product',
        string='Default Product Defective Goods (PoS)',
        index=True
    )

    product_default_pos_handle_discount_id = fields.Many2one(
        comodel_name='product.product',
        string='Default Product Handle Discount (PoS)',
        index=True
    )

    is_promotional_accounting_without_state_registration = fields.Boolean(
        default=False,
        string='Is Promotional Accounting Without State Registration'
    )
