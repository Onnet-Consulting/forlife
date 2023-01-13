from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime


class ProductTemplate(models.Model):
    _inherit = "product.template"

    detailed_type = fields.Selection(selection_add=[('asset', 'Asset')], ondelete={'asset': 'set default'})
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

    @api.depends('barcode_country')
    def _compute_barcode_product(self):
        for r in self:
            if r.detailed_type in ('service', 'product'):
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
        if self.env.context and self.env.context.get('prod_filter', False) and self.env.context.get('supplier_id', False):
            sql = """
            select id from product_product
            where product_tmpl_id in
                ( select distinct(product_tmpl_id)
                from product_supplierinfo
                where  partner_id  in 
                (select id from res_partner where name = %s))
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
        return super(ProductProduct, self).search(args, offset=offset, limit=limit, order=order, count=count)