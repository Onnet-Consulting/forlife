from odoo import fields, models, api
from odoo.exceptions import ValidationError

class PurchaseOrderExchangeRate(models.Model):
    _name = "purchase.order.exchange.rate"
    _description = 'Purchase Order Exchange Rate'

    ex_po_id = fields.Char('', compute='_compute_ex_po_id', store=1)

    @api.depends('purchase_order_id.order_line')
    def _compute_ex_po_id(self):
        for rec in self:
            orl_l_ids = []
            for line in rec.purchase_order_id.order_line:
                if rec.product_id.id == line.product_id.id:
                    po_l_id = line.id
                    while po_l_id in orl_l_ids:
                        po_l_id += 1
                    orl_l_ids.append(po_l_id)
                    rec.ex_po_id = po_l_id

    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.product', string='Mã sản phẩm')

    usd_amount = fields.Float(string='Thành tiền USF')  # đây chính là cột Thành tiền bên tab Sản phầm, a Trung đã viết trước
    vnd_amount = fields.Float(string='Thành tiền', compute='_compute_vnd_amount', store=1)

    # @api.depends('purchase_order_id.purchase_synthetic_ids.before_tax',
    #              'purchase_order_id.purchase_synthetic_ids.price_subtotal')
    # def _compute_vnd_amount(self):
    #     for rec in self:
    #         for item in rec.purchase_order_id.purchase_synthetic_ids:
    #             if rec.ex_po_id == item.syn_po_id and rec.product_id.id == item.product_id.id:
    #                 if not all(rec.purchase_order_id.purchase_synthetic_ids.mapped('before_tax')):
    #                     rec.vnd_amount = rec.vnd_amount - item.price_unit * item.quantity + rec.vnd_amount
    #                 else:
    #                     rec.vnd_amount = rec.vnd_amount + item.before_tax



    import_tax = fields.Float(string='% Thuế nhập khẩu')
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_tax_amount', store=1)

    special_consumption_tax = fields.Float(string='% Thuế tiêu thụ đặc biệt')
    special_consumption_tax_amount = fields.Float(string='Special Consumption Tax', compute='_compute_special_consumption_tax_amount', store=1)

    vat_tax = fields.Float(string='% Thuế GTGT')
    vat_tax_amount = fields.Float(string='VAT', compute='_compute_vat_tax_amount', store=1)

    # total_vnd_amount = fields.Float(string='Total VND Amount', compute='compute_vnd_amount')
    total_tax_amount = fields.Float(string='Total Tax Amount', compute='compute_tax_amount', store=1)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    qty_product = fields.Float(copy=True, string="Số lượng đặt mua")

    @api.constrains('import_tax', 'special_consumption_tax', 'vat_tax')
    def constrains_per(self):
        for item in self:
            if item.import_tax < 0:
                raise ValidationError('% thuế nhập khẩu phải >= 0 !')
            if item.special_consumption_tax < 0:
                raise ValidationError('% thuế tiêu thụ đặc biệt phải >= 0 !')
            if item.import_tax < 0:
                raise ValidationError('% thuế GTGT >= 0 !')

    @api.depends('vnd_amount', 'import_tax')
    def _compute_tax_amount(self):
        for rec in self:
            rec.tax_amount = rec.vnd_amount * rec.import_tax / 100\

    @api.depends('tax_amount', 'special_consumption_tax')
    def _compute_special_consumption_tax_amount(self):
        for rec in self:
            rec.special_consumption_tax_amount = (rec.vnd_amount + rec.tax_amount) * rec.special_consumption_tax / 100

    @api.depends('special_consumption_tax_amount', 'vat_tax')
    def _compute_vat_tax_amount(self):
        for rec in self:
            rec.vat_tax_amount = (rec.vnd_amount + rec.tax_amount + rec.special_consumption_tax_amount) * rec.vat_tax / 100

    @api.depends('vat_tax_amount')
    def compute_tax_amount(self):
        for rec in self:
            rec.total_tax_amount = rec.tax_amount + rec.special_consumption_tax_amount + rec.vat_tax_amount


