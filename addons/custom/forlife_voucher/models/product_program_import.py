from odoo import api, fields, models

class ProductProgramImport(models.Model):
    _name = 'product.program.import'

    _description = 'Sản phẩm áp dụng (Customize luồng import)'

    # program_vocher_id = fields.Many2one('program.voucher','Program Voucher')
    # product_id = fields.Many2one('product.product', string='Product')
    # barcode = fields.Char('Mã vạch', related='product_id.barcode')
    #
    # _sql_constraints = [
    #     ('unique_product_id', 'UNIQUE(product_id, program_vocher_id)', 'Product barcode must be unique!')
    # ]
    #
    # @api.model_create_multi
    # def create(self, vals_list):
    #     for idx, line in enumerate(vals_list):
    #         if ('active_model' in self._context and self._context.get('active_model')) and ('active_id' in self._context and self._context.get('active_id')):
    #             program_vocher = self.env['program.voucher'].sudo().search([('id','=',int(self._context.get('default_program_vocher_id')))])
    #             program_vocher.product_apply_ids = [(4, int(vals_list[idx]['product_id']))]
    #     return super(ProductProgramImport, self).create(vals_list)
    #
    # def unlink(self):
    #     for rec in self:
    #         rec.program_vocher_id.product_apply_ids = [(3, rec.product_id.id)]
    #     return super(ProductProgramImport, self).unlink()