# -*- coding: utf-8 -*-
#
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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

    sku_code = fields.Char(string="SKU Code", copy=False)

    expiration_date = fields.Datetime(string='Expiration Date', copy=False)
    days_before_alert = fields.Integer(string="Warning before (day)", copy=False, default=0)
    alert_date = fields.Datetime(string='Alert Date', compute='_compute_dates', store=True, readonly=False)
    product_expiry_reminded = fields.Boolean(string="Expiry has been reminded", default=False)
    brand_id = fields.Many2one('res.brand', related='product_tmpl_id.brand_id', string='Brand', readonly=0)

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


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['product.product']._alert_date_exceeded()
        if use_new_cursor:
            self.env.cr.commit()
