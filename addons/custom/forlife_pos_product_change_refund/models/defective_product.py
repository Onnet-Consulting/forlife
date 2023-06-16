from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductDefective(models.Model):
    _name = 'product.defective'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _description = 'Product Defective'

    store_id = fields.Many2one('store', 'Cửa hàng')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    quantity_defective_approved = fields.Integer('Số lượng lỗi đã duyệt')
    quantity_inventory_store = fields.Integer('Số lượng tồn theo cửa hàng', readonly=True, store=True, compute='compute_quantity_inventory_store')
    quantity_can_be_sale = fields.Integer('Số lượng lỗi có thể bán', tracking=True)
    price = fields.Float('Nguyên giá', related='product_id.lst_price')
    money_reduce = fields.Monetary('Số tiền giảm')
    percent_reduce = fields.Monetary('Phần trăm giảm')
    total_reduce = fields.Monetary('Tổng giảm', compute='_compute_total_reduce', store=True)
    defective_type_id = fields.Many2one('defective.type', 'Loại lỗi')
    detail_defective = fields.Char('Chi tiết lỗi')
    state = fields.Selection([('new', 'New'), ('waiting approve', 'Waiting Approve'), ('approved','Approved'),('refuse','Refuse')], string='Trạng thái', default='new')
    is_already_in_use = fields.Boolean(default=False)

    def unlink(self):
        for rec in self:
            if rec.is_already_in_use:
                raise ValidationError(_(f"KHông thể hoàn thành thao tác, có hàng lỗi đã được thực hiện bán!"))
        return super(ProductDefective, self).unlink()

    @api.depends('price', 'percent_reduce', 'money_reduce')
    def _compute_total_reduce(self):
        for rec in self:
            rec.total_reduce = (rec.price * rec.percent_reduce)/100 + rec.money_reduce

    def name_get(self):
        return [(rec.id, '%s' % rec.product_id.name) for rec in self]

    @api.depends('product_id', 'store_id')
    def compute_quantity_inventory_store(self):
        Quant = self.env['stock.quant']
        for rec in self:
            if rec.product_id and rec.store_id:
                available_quantity = Quant._get_available_quantity(product_id=rec.product_id, location_id=rec.store_id.warehouse_id.lot_stock_id, lot_id=None, package_id=None,
                                                                   owner_id=None, strict=False, allow_negative=False)
                if available_quantity:
                    rec.quantity_inventory_store = available_quantity
                else:
                    rec.quantity_inventory_store = 0

    def action_send_request_approve(self):
        self.state = 'waiting approve'
        self._send_mail_approve(self.id)

    def action_approve(self):
        self.ensure_one()
        product_defective_exits = self.env['product.defective'].sudo().search([('product_id','=',self.product_id.id), ('id','!=',self.id),('store_id','=',self.store_id.id)])
        if self.quantity_defective_approved > self.quantity_inventory_store - sum(product_defective_exits.mapped('quantity_can_be_sale')):
            raise ValidationError(_(f'Tồn kho của sản phẩm {self.product_id.name_get()[0][1]} không đủ trong kho {self.store_id.warehouse_id.name_get()[0][1]}'))
        self.quantity_can_be_sale = self.quantity_defective_approved
        self.state = 'approved'

    def action_refuse(self):
        self.state = 'refuse'

    def _send_mail_approve(self, id):
        mailTemplateModel = self.env['mail.template']
        irModelData = self.env['ir.model.data']
        templXmlId = irModelData._xmlid_to_res_id('forlife_pos_product_change_refund.email_template_handle_defective_product')
        baseUrl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirectUrl = baseUrl + '/web#id=%d&view_type=form&model=%s' % (id, self._name)
        if templXmlId:
            mailTmplObj = mailTemplateModel.browse(templXmlId)
            ctx = {
                'redirectUrl': redirectUrl,
            }
            mailTmplObj.with_context(**ctx).send_mail(id, force_send=True)

    @api.model
    def get_product_defective(self, store_id, products, store_name):
        if len(products) == 1:
            product_ids = str(tuple(products)).replace(',', '')
        else:
            product_ids = tuple(products)
        sql = f"SELECT pt.name as product_name, ppd.quantity_can_be_sale as quantity," \
              f"ppd.total_reduce as total_reduce,ppd.id as product_defective_id, ppd.detail_defective as detail_defective,ppd.product_id as product_id, dt.name as type_defective FROM product_defective ppd " \
              f"JOIN product_product pp on pp.id = ppd.product_id " \
              f"JOIN product_template pt on pt.id = pp.product_tmpl_id " \
              f"JOIN defective_type dt on dt.id = ppd.defective_type_id " \
              f"WHERE store_id = {store_id} AND product_id in {product_ids} AND quantity_can_be_sale >= 1 AND state = 'approved'"
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        for i in range(len(data)):
            data[i].update({
                'product_name': data[i]['product_name']['vi_VN'],
                'store_name': store_name,
                'id': i
            })
        return data
