from odoo.exceptions import UserError
from odoo import fields, models, api, _


class InheritPromotionProgram(models.Model):
    _inherit = 'promotion.program'

    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', index=True)
    product_discount_id = fields.Many2one(
        comodel_name='product.product', string='Discount Product', index=True,
        domain="[('is_promotion', '=', True)]"
    )

    @api.constrains('journal_id', 'product_discount_id')
    def _check_required_accounting_fields(self):
        for record in self:
            if not record.journal_id:
                raise UserError(_('Thiếu cấu hình Sổ nhật ký !'))
            if not record.product_discount_id:
                raise UserError(_('Thiếu cấu hình sản phẩm khyuến mãi !'))
