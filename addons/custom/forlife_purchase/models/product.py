from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime

list = [
    ('product', 'Sản phẩm lưu kho'),
    ('service', 'Dịch vụ'),
    ('asset', 'Tài sản'),
    ('event', 'Vé sự kiện')
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    detailed_type = fields.Selection(selection=list, string='Loại sản phẩm', default='product')
    type = fields.Selection(selection_add=[('asset', 'Asset')])

    product_type = fields.Selection(
        selection=[
            ('product', 'Hàng hóa'),
            ('service', 'Dịch vụ'),
            ('asset', 'Tài sản'),
        ],
        string='Loại hàng mua',
        required=True,
        copy=False,
        default='product',
    )
    barcode_country = fields.Many2one('forlife.barcode', string="Origin")
    barcode = fields.Char(
        'Barcode', copy=False, index='btree_not_null',
        help="International Article Number used for product identification.",
        compute="_compute_barcode_product", store=True, readonly=False)
    # thông tin công ty sản xuất sản phẩm
    product_company_id = fields.Many2one('res.partner', string='Company')
    expiration_date = fields.Date('Expiration Date')
    warning_date = fields.Date('Warning Date')
    pos_ok = fields.Boolean('Available on POS')
    x_type_cost_product = fields.Selection(
        selection=[
            ('internal_costs', 'Chi phí nội bộ'),
            ('labor_costs', 'Chi phí thuê ngoài'),
        ], string="Loại chi phí gia công")

    is_trade_discount = fields.Boolean(string="CKTM", default=False)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res['detailed_type'] = 'product'
        return res

    @api.depends('barcode_country')
    def _compute_barcode_product(self):
        for r in self:
            if r.barcode_country and r.detailed_type in ('service', 'product'):
                year_cr = datetime.datetime.now().year
                cr = self.env.cr
                query = '''
                    SELECT MAX(TEMP.AF) 
                    FROM 
                        (SELECT SUBSTRING(BARCODE, 0, LENGTH(BARCODE) - 6) AS BE, 
                         SUBSTRING(BARCODE, LENGTH(BARCODE) - 6, LENGTH(BARCODE)) AS AF, 
                         BARCODE 
                         FROM PRODUCT_TEMPLATE) AS TEMP 
                    WHERE TEMP.BE = '%s'
                    '''
                self.env.cr.execute(query % f'{r.barcode_country.barcode}{str(year_cr)[2:]}')
                recs = cr.dictfetchall()
                r.barcode = f"{r.barcode_country.barcode}{str(year_cr)[2:]}{str(int(recs[0].get('max')) + 1).rjust(7, '0') if recs[0].get('max') else '0000001'}"
            else:
                r.barcode = False


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context and self.env.context.get('purchase_type', False) == 'product' and self.env.context.get('supplier_id', False) and not self.env.context.get('is_passersby', False):
            sql = """
            select id from product_product
            where product_tmpl_id in
                ( select distinct(product_tmpl_id)
                from product_supplierinfo
                where  partner_id = %s)
            union 
            select id from product_product
            where product_tmpl_id not in 
                ( select distinct(product_tmpl_id)
                from product_supplierinfo)
            """ % (self.env.context.get('supplier_id'))
            self._cr.execute(sql)
            ids = [x[0] for x in self._cr.fetchall()]
            args.append(('id', 'in', ids))
            order = 'default_code'
        else:
            pass
        return super(ProductProduct, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        context = self.env.context
        if context and context.get('move_type', False) == 'in_invoice' and context.get('purchase_type', False) == 'product' and context.get('supplier_id', False) and not context.get('is_passersby', False):
            sql = """   
                select id
                from product_product
                where product_tmpl_id in ( 
                    select distinct(product_tmpl_id)
                    from product_supplierinfo
                    where partner_id = %s
                )
                
                union 
                
                select id 
                from product_product
                where product_tmpl_id not in ( 
                    select distinct(product_tmpl_id)
                    from product_supplierinfo
                )
            """ % (context.get('supplier_id'))
            self._cr.execute(sql)
            ids = [x[0] for x in self._cr.fetchall()]
            args.append(('id', 'in', ids))
        if context and context.get('move_type', False) == 'in_invoice' and context.get('purchase_type', False) == 'product' and context.get('supplier_id', False) and context.get('is_passersby', False):
            sql = """
                        select id from product_product
                        """
            self._cr.execute(sql)
            ids = [x[0] for x in self._cr.fetchall()]
            args.append(('id', 'in', ids))
        if context and context.get('type', False) == 'phantom':
            sql = """
                        select pp.id from product_product pp join product_template pt on pp.product_tmpl_id = pt.id where pt.detailed_type = 'product'
                        """
            self._cr.execute(sql)
            ids = [x[0] for x in self._cr.fetchall()]
            args.append(('id', 'in', ids))
        return super(ProductProduct, self).name_search(
            name, args, operator=operator, limit=limit)

    def name_get(self):
        if self.env.context.get('show_product_code'):
            return [(record.id, record.name or record.name) for record in self]
        return super().name_get()
