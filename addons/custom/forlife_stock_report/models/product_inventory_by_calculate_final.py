from odoo import fields, api, models, _
from datetime import datetime, timedelta
from itertools import chain


class CalculateFinalValue(models.Model):
    _inherit = 'calculate.final.value'
    _description = 'Tính giá trị cuối kỳ'

    product_inv_lines = fields.One2many('product.inventory.by.calculate.final', 'parent_id', string='Giá bình quân sản phẩm')
    product_inv_count = fields.Float(string='Số sản phẩm')

    def _sql_product_inv_line_str(self):
        return """
            with quantity_inventory_first as (
                select product_id, sum(qty_done) qty_done from (
                    select
                        sml.product_id,
                        sum(qty_done) as qty_done
                    from
                        stock_move_line sml
                    join stock_move sm on
                        sm.id = sml.move_id
                    join stock_location sl on
                        sml.location_dest_id = sl.id
                    join stock_picking sp on
                        sm.picking_id = sp.id
                    where
                        sm.date + interval '7 hours' < '{from_date}'
                        and sl."usage" = 'internal'
                        and sp.transfer_id is null
                        and sm.state = 'done'
                        and sm.company_id = {company_id}
                    group by sml.product_id
                union
                    select
                        sml.product_id,
                        - sum(qty_done) qty_done
                    from
                        stock_move_line sml
                    join stock_move sm on
                        sm.id = sml.move_id
                    join stock_location sl on
                        sml.location_id = sl.id
                    join stock_picking sp on
                        sm.picking_id = sp.id
                    where
                        sm.date + interval '7 hours' < '{from_date}'
                        and sl."usage" = 'internal'
                        and sp.transfer_id is null
                        and sm.state = 'done'
                        and sm.company_id = {company_id}
                    group by sml.product_id
                    
                ) master group by product_id
                
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
                        sm.date + interval '7 hours' >= '{from_date}'
                        and sm.date + interval '7 hours' <= '{to_date} 23:59:59'
                        and sl."usage" = 'internal'
                        and sp.transfer_id is null
                        and sm.state = 'done'
                        and sm.company_id = {company_id}
                    group by sml.product_id
                
                ), 
                quantity_inventory_out_period as (
                    select
                        sml.product_id,
                        sum(qty_done) qty_done
                    from
                        stock_move_line sml
                    join stock_move sm on
                        sm.id = sml.move_id
                    join stock_location sl on
                        sml.location_id = sl.id
                    join stock_picking sp on
                        sm.picking_id = sp.id
                    where
                        sm.date + interval '7 hours' >= '{from_date}'
                        and sm.date + interval '7 hours' <= '{to_date} 23:59:59'
                        and sl."usage" = 'internal'
                        and sp.transfer_id is null
                        and sm.state = 'done'
                        and sm.company_id = {company_id}
                    group by sml.product_id
                
                ),
                return_in_period as (
                
                    select
                        sml.product_id,
                        sum(qty_done) qty_done
                    from
                        stock_move_line sml
                    join stock_move sm on
                        sm.id = sml.move_id
                    join stock_location sl on
                        sml.location_id = sl.id
                    join stock_picking sp on
                        sm.picking_id = sp.id
                    where
                        sm.date + interval '7 hours' >= '{from_date}'
                        and sm.date + interval '7 hours' <= '{to_date} 23:59:59'
                        and sm.state = 'done'
                        and sl."usage" = 'internal'
                        and sp.transfer_id is null
                        and sp.x_is_check_return is true
                        and sm.company_id = {company_id}
                    group by sml.product_id
                ),
                amount_period as (
                	select product_id, sum(amount) amount from (
	                    select 
	                    pp.id product_id,
	                    sum(debit) amount
	                    
	                    from account_move_line aml 
	                    join account_move am on aml.move_id = am.id
	                    join product_product pp on aml.product_id = pp.id
	                    join product_template pt on pp.product_tmpl_id = pt.id
	                    join account_account aa on aml.account_id = aa.id
	                    join product_category pc on
	                        pt.categ_id = pc.id
	                    join ir_property ip on
	                        ip.res_id = 'product.category,' || pt.categ_id
	                        and ip."name" = 'property_stock_valuation_account_id'
	                        and ip.company_id = {company_id}
	                        and ip.value_reference = 'account.account,' || aa.id
	                        
	                    where 
	                    am.date >= '{from_date}'
                        and am.date <= '{to_date} 23:59:59'
                        and am.state = 'posted'
                        and (am.is_change_price = false or am.is_change_price is null)
	                    
	                    group by pp.id
	                    
	                    union all
	                    
	                    select 
	                    pp.id product_id,
	                    - sum(credit) amount
	                    
	                    from account_move_line aml 
	                    join account_move am on aml.move_id = am.id
	                    join product_product pp on aml.product_id = pp.id
	                    join product_template pt on pp.product_tmpl_id = pt.id
	                    join account_account aa on aml.account_id = aa.id
	                    join product_category pc on
	                        pt.categ_id = pc.id
	                    join ir_property ip on
	                        ip.res_id = 'product.category,' || pt.categ_id
	                        and ip."name" = 'property_stock_valuation_account_id'
	                        and ip.company_id = {company_id}
	                        and ip.value_reference = 'account.account,' || aa.id
	                    join stock_move sm on am.stock_move_id = sm.id and sm.state = 'done'
	                    join stock_picking sp on sm.picking_id = sp.id and sp.x_is_check_return is true
	                    
	                    where 
	                    am.date >= '{from_date}'
                        and am.date <= '{to_date} 23:59:59'
                        and am.state = 'posted'
                        and (am.is_change_price = false or am.is_change_price is null)
	                    
	                    group by pp.id
	                    
	                    union all
	                    
	                    select
                        pp.id product_id,
                        -sum(credit) amount
                        
                        from account_move_line aml 
                        join account_move am on aml.move_id = am.id
                        join account_move_purchase_order_rel ampor on am.id = ampor.account_move_id
                        join purchase_order po on ampor.purchase_order_id = po.id
                        join product_product pp on aml.product_id = pp.id
                        join product_template pt on pp.product_tmpl_id = pt.id
                        join product_category pc on pt.categ_id = pc.id
                        join ir_property ip on ip.res_id = 'product.category,' || pt.categ_id 
                        and ip."name" = 'property_stock_valuation_account_id' 
                        and ip.company_id = {company_id}
                        join account_account aa on 'account.account,' || aa.id = ip.value_reference and aml.account_id = aa.id
                        
                        where 
                        am.date >= '{from_date}'
                        and am.date <= '{to_date} 23:59:59'
                        and am.state = 'posted'
                        and am.company_id = {company_id}
                        and am.end_period_entry is true
                        and (am.is_change_price = false or am.is_change_price is null)
                        
                        group by 
                            pp.id

                    ) amount_period group by product_id
                ),
                amount_first as (
                	select product_id, sum(amount) amount from (
	                    select 
	                    pp.id product_id,
	                    sum(debit) amount
	                    
	                    from account_move_line aml 
	                    join account_move am on aml.move_id = am.id
	                    join product_product pp on aml.product_id = pp.id
	                    join product_template pt on pp.product_tmpl_id = pt.id
	                    join account_account aa on aml.account_id = aa.id
	                    join product_category pc on
	                        pt.categ_id = pc.id
	                    join ir_property ip on
	                        ip.res_id = 'product.category,' || pt.categ_id
	                        and ip."name" = 'property_stock_valuation_account_id'
	                        and ip.company_id = {company_id}
	                        and ip.value_reference = 'account.account,' || aa.id
	                        
	                    where 
	                    am.date <= '{from_date}'
	                    and am.state = 'posted'
	                    and (am.is_change_price = false or am.is_change_price is null)
	                    
	                    group by pp.id
	                    
	                    union all
	                    
	                    select 
	                    pp.id product_id,
	                    - sum(credit) amount
	                    
	                    from account_move_line aml 
	                    join account_move am on aml.move_id = am.id
	                    join product_product pp on aml.product_id = pp.id
	                    join product_template pt on pp.product_tmpl_id = pt.id
	                    join account_account aa on aml.account_id = aa.id
	                    join product_category pc on
	                        pt.categ_id = pc.id
	                    join ir_property ip on
	                        ip.res_id = 'product.category,' || pt.categ_id
	                        and ip."name" = 'property_stock_valuation_account_id'
	                        and ip.company_id = {company_id}
	                        and ip.value_reference = 'account.account,' || aa.id
	                    join stock_move sm on am.stock_move_id = sm.id and sm.state = 'done'
	                    join stock_picking sp on sm.picking_id = sp.id and sp.x_is_check_return is true
	                    
	                    where 
	                    am.date <= '{from_date}'
	                    and am.state = 'posted'
	                    and (am.is_change_price = false or am.is_change_price is null)
	                    
	                    group by pp.id
	                    
	                    union all
	                    
	                    select
                        pp.id product_id,
                        -sum(credit) amount
                        
                        from account_move_line aml 
                        join account_move am on aml.move_id = am.id
                        join account_move_purchase_order_rel ampor on am.id = ampor.account_move_id
                        join purchase_order po on ampor.purchase_order_id = po.id
                        join product_product pp on aml.product_id = pp.id
                        join product_template pt on pp.product_tmpl_id = pt.id
                        join product_category pc on pt.categ_id = pc.id
                        join ir_property ip on ip.res_id = 'product.category,' || pt.categ_id 
                        and ip."name" = 'property_stock_valuation_account_id' 
                        and ip.company_id = {company_id}
                        join account_account aa on 'account.account,' || aa.id = ip.value_reference and aml.account_id = aa.id
                        
                        where 
                        am.date <= '{from_date}'
                        and am.state = 'posted'
                        and am.company_id = {company_id}
                        and am.end_period_entry is true
                        and (am.is_change_price = false or am.is_change_price is null)
                        
                        group by 
                            pp.id
                    ) amount_first group by product_id
                )
                
                select 
                    {parent_id} parent_id,
                    pp.id product_id,
                    qif.qty_done qty_begin_period,
                    (qiip.qty_done - coalesce(rip.qty_done, 0)) qty_in_period,
                    ap.amount amount_period,
                    af.amount amount_begin_period
                    
                from product_product pp 
                left join product_template pt on pp.product_tmpl_id = pt.id
                left join quantity_inventory_first qif on pp.id = qif.product_id
                left join quantity_inventory_in_period qiip on pp.id = qiip.product_id
                left join quantity_inventory_out_period qiop on pp.id = qiop.product_id
                left join return_in_period rip on pp.id = rip.product_id
                left join amount_period ap on pp.id = ap.product_id
                left join amount_first af on pp.id = af.product_id
                join product_category pc on pt.categ_id = pc.id
                join product_category_type pct on pc.category_type_id = pct.id
                where pt.detailed_type = 'product' {where}
                and pct.code = {category_type} 
                and (qif.qty_done > 0 or qiip.qty_done > 0 or rip.qty_done > 0)
        
        """

    def get_data_unit_price_product(self):
        self.product_inv_lines.unlink()
        sql_product_end = f"""
                    select distinct product_end_id from list_exported_goods_diff legd 
                    where legd.product_end_id is not null and legd.parent_id in (select id from calculate_final_value cfv where cfv."month" = '{self.month}' and cfv."year" = '{self.year}'
                    and cfv.category_type_id = '{self.category_type_id}' order by cfv.id desc limit 1 offset 1)
                """
        if self.product_type == 'end':
            self._cr.execute(sql_product_end)
            product_ids = self._cr.fetchall()
            if product_ids:
                query = self._sql_product_inv_line_str().format(
                    company_id=self.env.company.id,
                    from_date=self.from_date,
                    to_date=self.to_date,
                    from_date_begin=self.from_date - timedelta(days=1),
                    parent_id=self.id,
                    where=f'and pp.id = any(array{list(chain.from_iterable(product_ids))})' if product_ids else '',
                    category_type="any(array['2', '3'])" if self.category_type_id == 'npl_ccdc' else "any(array['1'])"
                )
            else:
                query = False
        else:
            query = self._sql_product_inv_line_str().format(
                company_id=self.env.company.id,
                from_date=self.from_date,
                to_date=self.to_date,
                from_date_begin=self.from_date - timedelta(days=1),
                parent_id=self.id,
                where=f'',
                category_type="any(array['2', '3'])" if self.category_type_id == 'npl_ccdc' else "any(array['1'])"
            )
        if query:
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
            "name": _("Đơn giá tồn cuối kỳ"),
            'view_mode': 'tree',
        }
        return result

    def list_diff_amount(self):
        self.ensure_one()
        diff_line = self.goods_diff_lines.ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "list.exported.goods.diff",
            "domain": [('id', 'in', diff_line)],
            "context": {"create": False},
            "name": _("Bảng kê chênh lệch"),
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
    amount_product = fields.Float(string='Đơn giá bình quân cuối kỳ', compute='_compute_amount_product', store=True, digits=(16, 2))
    date = fields.Date(string='Ngày chốt tồn', related='parent_id.to_date', store=True)

    @api.depends('qty_begin_period', 'qty_in_period', 'amount_begin_period', 'amount_period')
    def _compute_amount_product(self):
        for rec in self:
            if (rec.qty_begin_period + rec.qty_in_period) != 0:
                rec.amount_product = (rec.amount_period + rec.amount_begin_period) / (
                            rec.qty_begin_period + rec.qty_in_period)
            else:
                rec.amount_product = 0
