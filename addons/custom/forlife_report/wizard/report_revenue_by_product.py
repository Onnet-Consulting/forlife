# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ReportRevenueByProduct(models.TransientModel):
    _name = 'report.revenue.by.product'
    _inherit = 'report.base'
    _description = 'Report revenue by product'

    from_date = fields.Date(string='From date', required=True, default="2022-01-01")
    to_date = fields.Date(string='To date', required=True,default="2022-12-12")
    all_products = fields.Boolean(string='All products', default=False)
    all_warehouses = fields.Boolean(string='All warehouses', default=False)
    product_ids = fields.Many2many('product.product', string='Products')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.from_date > record.to_date:
                raise ValidationError(_('From Date must be less than or equal To Date'))

    def view_report(self):
        action = self.env.ref('forlife_report.report_revenue_by_product_client_action').read()[0]
        return action

    def _get_query(self):
        query = """
select *
from pos_order_line pol
         left join product_product pp on pol.product_id = pp.id
         left join product_template pt on pp.product_tmpl_id = pt.id
         left join uom_uom uom on pt.uom_id = uom.id
         left join pos_order on pol.order_id = pos_order.id

        """

    def get_data(self):
        self._cr.execute('select name from res_partner')
        data = self._cr.dictfetchall()
        return data
