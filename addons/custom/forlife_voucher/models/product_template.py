from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    voucher = fields.Boolean('Voucher')
    program_voucher_ids = fields.One2many('program.voucher','product_id')