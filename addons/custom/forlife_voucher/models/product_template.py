from odoo import api, fields, models
from odoo.osv import expression

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if 'filter_product_follow_type' in self._context and self._context.get('filter_product_follow_type'):
            if self._context.get('filter_product_follow_type') == 'v':
                products = self.search([('detailed_type', '=', 'product'), ('program_voucher_id', '=', False)])
                domain = expression.AND([domain, [('id', 'in', products.ids)]])
            else:
                products = self.search([('detailed_type', '=', 'service'), ('program_voucher_id', '=', False)])
                domain = expression.AND([domain, [('id', 'in', products.ids)]])
        return super(ProductTemplate, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if 'filter_product_follow_type' in self._context and self._context.get('filter_product_follow_type'):
            if self._context.get('filter_product_follow_type') == 'v':
                products = self.sudo().search([('detailed_type','=','product'),('program_voucher_id','=',False)])
                args = expression.AND([args, [('id', 'in', products.ids)]])
            else:
                products = self.sudo().search([('detailed_type', '=', 'service'),('program_voucher_id','=',False)])
                args = expression.AND([args, [('id', 'in', products.ids)]])
        res = super(ProductTemplate, self)._name_search(name, args, operator, limit, name_get_uid)
        return res

    @api.onchange('voucher')
    def _onchange_voucher(self):
        if self.voucher:
            self.list_price = 0.0

    voucher = fields.Boolean('Voucher')
    program_voucher_id = fields.Many2one('program.voucher', readonly=True, copy=False)


    def write(self, vals):
        if 'program_voucher_id' in vals and vals['program_voucher_id']:
            product_include = self.search([('program_voucher_id', '=', vals['program_voucher_id'])])
            if product_include:
                product_include.program_voucher_id = False
        return super(ProductTemplate, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if 'program_voucher_id' in vals_list and vals_list['program_voucher_id']:
            product_include = self.search([('program_voucher_id', '=', vals_list['program_voucher_id'])])
            if product_include:
                product_include.program_voucher_id = False
        return super(ProductTemplate, self).create(vals_list)

    def get_notification_id(self, price):
        if len(self.product_variant_ids) < 1:
            return False
        elif len(self.product_variant_ids) == 1:
            return self.product_variant_ids.notification_id
        else:
            product = self.product_variant_ids.filtered(lambda f: f.price == price)
            return (product and product[0].notification_id) or False
