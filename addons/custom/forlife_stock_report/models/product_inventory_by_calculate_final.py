from odoo import fields, api, models, _
from datetime import datetime, timedelta


class CalculateFinalValue(models.Model):
    _inherit = 'calculate.final.value'
    _description = 'Tính giá trị cuối kỳ'

    product_inv_lines = fields.One2many('product.inventory.by.calculate.final', 'parent_id', string='Giá bình quân sản phẩm')
    product_inv_count = fields.Float(string='Số sản phẩm')

    def _sql_product_inv_line_str(self):
        return """
            with product_begin as (
                select 
                    pp.id,
                    pibpl.qty_product,
                    pibpl.amount_product
                    
                from product_product pp 
                join product_template pt on pp.product_tmpl_id = pt.id
                join product_category pc on pt.categ_id = pc.id
                join product_category_type cpt on pc.category_type_id = cpt.id
                join product_inventory_by_period_line pibpl on pp.id = pibpl.product_id and pibpl.date = '{from_date_begin}'
                
                where cpt.code = {category_type} and pibpl.company_id = {company_id}
                ),
                quantity_inventory_in_period as (
                    select
                        sml.product_id,
                        sum(qty_done) qty_done
                    from
                        stock_move_line sml
                    join stock_move sm on
                        sm.id = sml.move_id
                    join stock_location sl on
                        sml.location_dest_id = sl.id
                    join stock_picking sp on
                        sm.picking_id = sp.id
                    where
                        sm.date >= '{from_date}'
                        and sm.date <= '{to_date} 23:59:59'
                        and sl."usage" = 'internal'
                        and sp.transfer_id is null
                        and sm.state = 'done'
                        and sm.company_id = {company_id}
                    group by sml.product_id
                
                )
                
                select 
                    {parent_id} parent_id,
                    pb.id product_id,
                    pb.qty_product qty_begin_period,
                    pb.amount_product amount_begin_period,
                    qiip.qty_done qty_in_period
                from product_begin pb left join quantity_inventory_in_period qiip on 
                pb.id = qiip.product_id
        
        """

    def get_data_unit_price_product(self):
        self.product_inv_lines.unlink()
        query = self._sql_product_inv_line_str().format(
            company_id=self.env.company.id,
            from_date=self.from_date,
            to_date=self.to_date,
            from_date_begin=self.from_date - timedelta(days=1),
            parent_id=self.id,
            category_type="any(array['2', '3'])" if self.category_type_id == 'npl_ccdc' else "any(array['1'])"
        )
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        pinv = self.env['product.inventory.by.calculate.final'].create(data)
        self.write({
            'product_inv_count': len(pinv),
            'state': 'step1'
        })

    def action_view_pinv(self):
        self.ensure_one()
        move_ids = self.product_inv_lines.ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "product.inventory.by.calculate.final",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False},
            "name": _("Bút toán chênh lệch"),
            'view_mode': 'tree',
        }
        return result


class ProductInventoryLine(models.Model):
    _name = 'product.inventory.by.calculate.final'
    _description = 'Tồn kho sản phẩm theo kỳ chi tiết'
    _rec_name = 'product_id'

    parent_id = fields.Many2one('calculate.final.value', string='Kỳ chốt tính giá', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    qty_begin_period = fields.Float(string='Tồn đầu')
    qty_in_period = fields.Float(string='Nhập trong kỳ')
    amount_begin_period = fields.Float(string='Giá trị đầu kỳ', digits=(16, 2))
    amount_period = fields.Float(string='Giá trị nhập trong kỳ', digits=(16, 2))
    amount_product = fields.Float(string='Đơn giá bình quân cuối kỳ')
    date = fields.Date(string='Ngày chốt tồn', related='parent_id.to_date', store=True)
