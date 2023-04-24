# -*- coding: utf-8 -*-
#
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class ProducAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    code = fields.Char(string="Mã", required=True)

    _sql_constraints = [
        ('value_code_uniq', 'unique (code, attribute_id)', "Bạn không thể tạo hai mã có cùng giá trị cho cùng một thuộc tính.")
    ]


class ProducProduct(models.Model):
    _inherit = "product.product"

    sku_code = fields.Char(string="SKU Code", copy=False)

    expiration_date = fields.Datetime(string='Expiration Date', copy=False)
    days_before_alert = fields.Integer(string="Warning before (day)", copy=False, default=0)
    alert_date = fields.Datetime(string='Alert Date', compute='_compute_dates', store=True, readonly=False)
    product_expiry_reminded = fields.Boolean(string="Expiry has been reminded", default=False)

    @api.depends('expiration_date', 'days_before_alert')
    def _compute_dates(self):
        for product in self:
            if product.expiration_date:
                product.alert_date = product.expiration_date - datetime.timedelta(days=product.days_before_alert)
                if product.product_expiry_reminded:
                    product.product_expiry_reminded = False
            else:
                product.alert_date = False

    @api.model
    def _alert_date_exceeded(self):
        alert_products = self.env['product.product'].search([
            ('alert_date', '!=', False),
            ('alert_date', '<=', fields.Date.today()),
            ('product_expiry_reminded', '=', False)])

        for product in alert_products:
            product.activity_schedule(
                'forlife_base.mail_activity_type_alert_date_reached',
                user_id=product.responsible_id.id or SUPERUSER_ID,
                note=_("The alert date has been reached for this product")
            )
        alert_products.write({
            'product_expiry_reminded': True
        })

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            product_ids = []
            if operator in positive_operators:
                product_ids = list(
                    self._search([('barcode', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid))
                if not product_ids:
                    product_ids = list(
                        self._search([('default_code', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid))

            if not product_ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                product_ids = list(self._search(args + [('default_code', operator, name)], limit=limit))
                if not limit or len(product_ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(product_ids)) if limit else False
                    product2_ids = self._search(args + [('name', operator, name), ('id', 'not in', product_ids)],
                                                limit=limit2, access_rights_uid=name_get_uid)
                    product_ids.extend(product2_ids)
            elif not product_ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = expression.OR([
                    ['&', ('default_code', operator, name), ('name', operator, name)],
                    ['&', ('default_code', '=', False), ('name', operator, name)],
                ])
                domain = expression.AND([args, domain])
                product_ids = list(self._search(domain, limit=limit, access_rights_uid=name_get_uid))
            if not product_ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    product_ids = list(self._search([('default_code', '=', res.group(2))] + args, limit=limit,
                                                    access_rights_uid=name_get_uid))
            # still no results, partner in context: search on supplier info as last hope to find something
            if not product_ids and self._context.get('partner_id'):
                suppliers_ids = self.env['product.supplierinfo']._search([
                    ('partner_id', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)], access_rights_uid=name_get_uid)
                if suppliers_ids:
                    product_ids = self._search([('product_tmpl_id.seller_ids', 'in', suppliers_ids)], limit=limit,
                                               access_rights_uid=name_get_uid)
        else:
            product_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return product_ids


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['product.product']._alert_date_exceeded()
        if use_new_cursor:
            self.env.cr.commit()
