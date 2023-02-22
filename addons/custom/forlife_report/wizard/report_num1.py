# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ReportNum1(models.TransientModel):
    _name = 'report.num1'
    _inherit = 'report.base'
    _description = 'Report revenue by product'

    from_date = fields.Date(string='From date', required=True)
    to_date = fields.Date(string='To date', required=True)
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
        self.ensure_one()
        action = self.env.ref('forlife_report.report_num_1_client_action').read()[0]
        return action

    def print_xlsx(self):
        ...

    def _get_query(self):
        self.ensure_one()
        user_lang_code = self.env.user.lang
        tz_offset = self.tz_offset
        query = f"""
select row_number() over (order by pt.name)                                      as num,
       pol.product_id                                                            as product_id,
       pp.barcode                                                                as product_barcode,
       coalesce(pt.name::json -> '{user_lang_code}', pt.name::json -> 'en_US')   as product_name,
       coalesce(uom.name::json -> '{user_lang_code}', uom.name::json -> 'en_US') as uom_name,
       pol.price_unit                                                            as price_unit,
       pol.qty                                                                   as qty,
       pol.discount                                                              as discount_percent,
       pol.price_subtotal                                                        as amount_without_tax,
       pol.price_subtotal_incl                                                   as amount_with_tax
from pos_order_line pol
         left join product_product pp on pol.product_id = pp.id
         left join product_template pt on pp.product_tmpl_id = pt.id
         left join uom_uom uom on pt.uom_id = uom.id
         left join pos_order po on pol.order_id = po.id
where po.company_id = %s
  and po.state in ('paid', 'done', 'invoiced')
  and po.date_order + interval '{tz_offset} hours' >= %s
  and po.date_order + interval '{tz_offset} hours' <= %s
        """
        return query

    def _get_query_params(self):
        self.ensure_one()
        from_date = self.convert_datetime_to_utc(self.from_date)
        to_date = self.convert_datetime_to_utc(self.to_date)
        params = [self.company_id.id, from_date, to_date]
        return params

    def get_data(self):
        self.ensure_one()
        query = self._get_query()
        params = self._get_query_params()
        self._cr.execute(query, params)
        data = self._cr.dictfetchall()
        return data
