# -*- coding: utf-8 -*-
#
import re
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

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_brand_default(self):
        user_id = self.env['res.users'].browse(self._uid)
        if not user_id:
            return
        return user_id.brand_default_id

    brand_id = fields.Many2one('res.brand', string='Brand', default=_get_brand_default)


class ProducProduct(models.Model):
    _inherit = "product.product"

    expiration_date = fields.Datetime(string='Expiration Date', copy=False)
    days_before_alert = fields.Integer(string="Warning before (day)", copy=False, default=0)
    alert_date = fields.Datetime(string='Alert Date', compute='_compute_dates', store=True, readonly=False)
    product_expiry_reminded = fields.Boolean(string="Expiry has been reminded", default=False)
    brand_id = fields.Many2one('res.brand', related='product_tmpl_id.brand_id', string='Brand', readonly=1)

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

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _rec_names_search = ['barcode']

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # Only use the product.product heuristics if there is a search term and the domain
        # does not specify a match on `product.template` IDs.
        if not name or any(term[0] == 'id' for term in (args or [])):
            return super(ProductTemplate, self)._name_search(name=name, args=args, operator=operator, limit=limit,
                                                             name_get_uid=name_get_uid)

        Product = self.env['product.product']
        templates = self.browse([])
        while True:
            domain = templates and [('product_tmpl_id', 'not in', templates.ids)] or []
            args = args if args is not None else []
            # Product._name_search has default value limit=100
            # So, we either use that value or override it to None to fetch all products at once
            kwargs = {} if limit else {'limit': None}
            products_ids = Product._name_search(name, args + domain, operator=operator, name_get_uid=name_get_uid,
                                                **kwargs)
            products = Product.browse(products_ids)
            new_templates = products.mapped('product_tmpl_id')
            if new_templates & templates:
                """Product._name_search can bypass the domain we passed (search on supplier info).
                   If this happens, an infinite loop will occur."""
                break
            templates |= new_templates
            if (not products) or (limit and (len(templates) > limit)):
                break

        searched_ids = set(templates.ids)
        # some product.templates do not have product.products yet (dynamic variants configuration),
        # we need to add the base _name_search to the results
        # FIXME awa: this is really not performant at all but after discussing with the team
        # we don't see another way to do it
        tmpl_without_variant_ids = []
        # if not limit or len(searched_ids) < limit:
        #     tmpl_without_variant_ids = self.env['product.template'].search(
        #         [('id', 'not in', self.env['product.template']._search([('product_variant_ids.active', '=', True)]))]
        #     )
        if tmpl_without_variant_ids:
            domain = expression.AND([args or [], [('id', 'in', tmpl_without_variant_ids.ids)]])
            searched_ids |= set(super(ProductTemplate, self)._name_search(
                name,
                args=domain,
                operator=operator,
                limit=limit,
                name_get_uid=name_get_uid))

        # re-apply product.template order + name_get
        return super(ProductTemplate, self)._name_search(
            '', args=[('id', 'in', list(searched_ids))],
            operator='ilike', limit=limit, name_get_uid=name_get_uid)
