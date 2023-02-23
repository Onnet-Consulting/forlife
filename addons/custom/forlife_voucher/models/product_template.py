from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    voucher = fields.Boolean('Voucher')
    program_voucher_id = fields.Many2one('program.voucher', compute='compute_program', inverse='program_inverse')
    program_voucher_ids = fields.One2many('program.voucher', 'product_id')

    @api.depends('program_voucher_ids')
    def compute_program(self):
        if len(self.program_voucher_ids) > 0:
            self.program_voucher_id = self.program_voucher_ids[0]

    def program_inverse(self):
        if len(self.program_voucher_ids) > 0:
            program = self.env['program.voucher'].browse(self.program_voucher_ids[0].id)
            program.product_id = False
        self.program_voucher_id.product_id = self