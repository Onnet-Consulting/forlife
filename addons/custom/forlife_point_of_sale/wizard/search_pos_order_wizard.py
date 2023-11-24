# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SearchPosOrderWizard(models.TransientModel):
    _name = 'search.pos.order.wizard'
    _description = 'Tra cứu đơn hàng'
    _rec_name = 'phone_number'

    phone_number = fields.Char('Số điện thoại', default='0', required=1)
    product_id = fields.Many2one('product.product', "Sản phẩm")
    from_date = fields.Date('Từ ngày')
    to_date = fields.Date('Đến ngày')
    result_po_ids = fields.Many2many(comodel_name='pos.order', string='Kết quả tra cứu')

    def btn_search(self):
        user = self.env.user
        format_date = "and to_date(to_char(po.date_order + interval '7 hours', 'YYYY-MM-DD'), 'YYYY-MM-DD')"
        sql = f"""
        with temp as (select distinct po.id as po_id
                      from pos_order po
                               join res_partner rp on po.partner_id = rp.id
                               {'join pos_order_line pol on po.id = pol.order_id' if self.product_id else ''}
                      where rp.phone = '{self.phone_number}'
                        {'and po.brand_id = any(array {})'.format(user.brand_ids.ids) if user.brand_ids else ''}
                        {'and pol.product_id = {}'.format(self.product_id.id) if self.product_id else ''}
                        {f"{format_date} >= '{self.from_date}'" if self.from_date else ''}
                        {f"{format_date} <= '{self.to_date}'" if self.to_date else ''})
        select json_agg(po_id) as list_po
        from temp
        """
        self._cr.execute(sql)
        list_po = self._cr.fetchone()[0] or []
        self.result_po_ids = [(6, 0, list_po)]
