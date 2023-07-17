from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductionOrder(models.Model):
    _name = 'production.order'
    _description = 'Attach Ingredients/Product Separation'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'product_id'


    @api.model
    def create(self, vals):
        res = super(ProductionOrder, self).create(vals)
        if res.product_id:
            res.product_id.x_check_npl = True
        return res

    def write(self, vals):
        if 'product_id' in vals:
            if vals.get('product_id') != self.product_id.id:
                product_npl_id = self.env['product.product'].browse(vals.get('product_id'))
                product_npl_id.x_check_npl = True
                self.product_id.x_check_npl = False
        return super(ProductionOrder, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec.product_id:
                rec.product_id.x_check_npl = False
        return super(ProductionOrder, self).unlink()

    code = fields.Char('Reference')
    sequence = fields.Integer('Sequence')
    type = fields.Selection([
        ('normal', 'Attach Ingredients')], 'BoM Type', default='normal', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    production_uom = fields.Many2one('uom.uom', string='Đơn vị', related='product_id.uom_id')
    order_line_ids = fields.One2many('production.order.line', 'order_id', 'Production Order Lines', copy=True)
    product_qty = fields.Float('Quantity', default=1.0, digits='Unit of Measure', required=True)
    invoice_status_fake = fields.Selection([
        ('no', 'Chưa nhận'),
        ('to invoice', 'Dở dang'),
        ('invoiced', 'Hoàn thành'),
    ], string='Trạng thái hóa đơn', readonly=True, copy=False, default='no')

    company_id = fields.Many2one('res.company',
                                 string='Công ty',
                                 default=lambda self: self.env.company)


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
    price = fields.Float(string='Giá', compute='compute_price', readonly=False, store=1)

    company_id = fields.Many2one('res.company',
                                 string='Công ty', required=True,
                                 default=lambda self: self.env.company)

    @api.constrains('product_qty')
    def constrains_product_qty(self):
        for rec in self:
            if rec.product_qty <= 0:
                raise ValidationError(_('quantity cannot be zero or negative !!'))

    @api.depends('product_id')
    def compute_price(self):
        for rec in self:
            rec.price = rec.product_id.lst_price
