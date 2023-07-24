from odoo import models, fields


class InheritResCompany(models.Model):
    _inherit = 'res.company'

    product_default_pos_defective_goods_id = fields.Many2one(
        comodel_name='product.product',
        string='Default Product Defective Goods (PoS)',
    )
    journal_default_pos_defective_goods_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default Journal Defective Goods (PoS)',
    )

    product_default_pos_handle_discount_id = fields.Many2one(
        comodel_name='product.product',
        string='Default Product Handle Discount (PoS)',
    )
    journal_default_pos_handle_discount_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default Journal Handle Discount (PoS)',
    )

    product_default_pos_return_goods_id = fields.Many2one(
        comodel_name='product.product',
        string='Default Product Change/Return Goods (PoS)',
    )
    journal_default_pos_return_goods_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default Journal Change/Return Goods (PoS)',
    )

    is_promotional_accounting_without_state_registration = fields.Boolean(
        default=False,
        string='Is Promotional Accounting Without State Registration'
    )
