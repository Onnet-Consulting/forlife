from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    voucher = fields.Boolean('Voucher')
    program_voucher_id = fields.Many2one('program.voucher')

    # @api.onchange('program_voucher_id')
    # def onchange_program_id(self):
    #     product_include = self.search([('program_voucher_id', '=', self.program_voucher_id.id)])
    #     if product_include:
    #         product_include.program_voucher_id = False

    def write(self, vals):
        if 'program_voucher_id' in vals and vals['program_voucher_id']:
            product_include = self.search([('program_voucher_id', '=', vals['program_voucher_id'])])
            if product_include:
                product_include.program_voucher_id = False
        return super(ProductTemplate, self).write(vals)

    @api.model
    def create(self, vals_list):
        if 'program_voucher_id' in vals_list and vals_list['program_voucher_id']:
            product_include = self.search([('program_voucher_id', '=', vals_list['program_voucher_id'])])
            if product_include:
                product_include.program_voucher_id = False
        return super(ProductTemplate, self).create(vals_list)