from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductionOrder(models.Model):
    _name = 'production.order'
    _description = 'Attach Ingredients/Product Separation'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'product_id'


    code = fields.Char('Reference')
    sequence = fields.Integer('Sequence')
    type = fields.Selection([
        ('normal', 'Attach Ingredients'),
        ('phantom', 'Product Separation')], 'BoM Type', default='normal', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    production_uom = fields.Many2one('uom.uom', string='Đơn vị', related='product_id.uom_id')
    order_line_ids = fields.One2many('production.order.line', 'order_id', 'Production Order Lines', copy=True)
    product_qty = fields.Float('Quantity', default=1.0, digits='Unit of Measure', required=True)
    domain_product_ids = fields.Many2many('product.product', string='Selected Products', compute='compute_product_id')

    @api.constrains('product_id')
    def _constraint_product_id(self):
        for rec in self:
            if rec.search_count(
                    [('product_id', '=', rec.product_id.id), ('id', '!=', rec.id)]):
                raise ValidationError(_('Sản phẩm %s đã được khai báo nguyên phụ liệu/phân tách sản phẩm, bạn cần kiểm tra lại!') % rec.product_id.name)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu NPL'),
            'template': '/purchase_request/static/src/xlsx/file import npl.xlsx?download=true'
        }]

    @api.depends('type')
    def compute_product_id(self):
        data_search = self.data_search([('detailed_type', '=', 'product')])
        for rec in self:
            if rec.type == 'phantom':
                self.domain_product_ids = [
                    (6, 0, [item.id for item in data_search])]
            else:
                self.domain_product_ids = [
                    (6, 0, [item.id for item in self.data_search([])])]

    def data_search(self, domain):
        return self.env['product.product'].search(domain)


class ProductionOrderLine(models.Model):
    _name = 'production.order.line'
    _description = 'Production Order Line'

    product_id = fields.Many2one('product.product', 'Component', required=True)
    product_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)
    sequence = fields.Integer('Sequence', default=1,)
    order_id = fields.Many2one('production.order', ondelete='cascade', required=True)
    uom_id = fields.Many2one(related="product_id.uom_id")
    attachments_count = fields.Integer('Attachments Count')
    price = fields.Float(string='Price', compute='compute_price', readonly=False, store=1)

    @api.constrains('product_qty')
    def constrains_product_qty(self):
        for rec in self:
            if rec.product_qty <= 0:
                raise ValidationError(_('quantity cannot be zero or negative !!'))

    @api.depends('product_id')
    def compute_price(self):
        for rec in self:
            rec.price = rec.product_id.lst_price
