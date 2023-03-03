from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    voucher = fields.Boolean('Voucher')
    program_voucher_id = fields.Many2one('program.voucher')
    price = fields.Float(string='Price', digits='Product Price')

    @api.onchange('program_voucher_id')
    def onchange_program_id(self):
        product_include = self.search([('program_voucher_id', '=', self.program_voucher_id.id)])
        if product_include:
            product_include.program_voucher_id = False
