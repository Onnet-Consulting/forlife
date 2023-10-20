from odoo import fields, api, models
import datetime
from datetime import timedelta


class ProductInventory(models.Model):
    _name = 'product.inventory.by.period'
    _description = 'Chốt tồn sản phẩm'

    name = fields.Char(compute='compute_from_to_date', string='Kỳ tính giá', store=True)
    month = fields.Char(string='Tháng', default=fields.Date.today().month, required=True)
    year = fields.Char(string='Năm', default=fields.Date.today().year, required=True)
    from_date = fields.Date(string='Từ ngày', compute='compute_from_to_date', store=True)
    to_date = fields.Date(string='Đến ngày', compute='compute_from_to_date', store=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    inv_lines = fields.One2many('product.inventory.by.period.line', 'parent_id', string='Chi tiết tồn')
    state = fields.Selection([
        ('draft', 'Dự thảo'),
        ('done', 'Đã chốt')
    ], default='draft', string='Trạng thái')

    def first_and_last_day_of_month(self, year, month):
        # Tạo một ngày đầu tiên của tháng
        first_day = datetime.date(year, month, 1)
        # Xác định tháng tiếp theo
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        # Tạo ngày cuối cùng của tháng bằng cách lấy ngày cuối cùng của tháng trước và trừ đi một ngày
        last_day = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)
        return first_day, last_day

    @api.depends('month', 'year')
    def compute_from_to_date(self):
        for rec in self:
            current_date = datetime.date.today()
            current_year = current_date.replace(year=int(rec.year)).year
            current_month = current_date.replace(year=int(rec.year), month=int(rec.month)).month
            first, last = self.first_and_last_day_of_month(current_year, current_month)
            rec.from_date = first
            rec.to_date = last
            rec.name = 'Tồn sản phẩm tháng %s năm %s' % (rec.month, rec.year)

    def _sql_string_inv(self):
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
                        and sm.origin_returned_move_id is not null
                        and sm.company_id = {company_id}
                    group by sml.product_id
                ),
                amount_period as (
                    select product_id, sum(amount) amount from (
                        select
                            pp.id product_id,
                            sum(aml.debit) - sum(aml.credit) amount
                        
                        from account_move am
                        join account_move_line aml on
                        am.id = aml.move_id
                        join product_product pp on
                        aml.product_id = pp.id
                        join product_template pt on
                        pp.product_tmpl_id = pt.id
                        join account_account aa on aml.account_id = aa.id
                        join product_category pc on
                            pt.categ_id = pc.id
                        join ir_property ip on
                            ip.res_id = 'product.category,' || pt.categ_id
                            and ip."name" = 'property_stock_valuation_account_id'
                            and ip.company_id = {company_id}
                            and ip.value_reference = 'account.account,' || aa.id
                        
                        where 
                        am.invoice_type in ('increase', 'decrease') 
                        and aa.code like '3319%' 
                        and am.state = 'posted'
                        and am.payment_state != 'reversed'
                        and am.date >= '{from_date}' and am.date <= '{to_date} 23:59:59'
                        and am.company_id = {company_id}
                        
                        group by
                        pp.id
                    
                        union
                        select
                            product_id,
                            sum(amount)
                        from
                            (
                            select
                                pp.id product_id,
                                aml.debit amount,
                                am.name
                            from
                                stock_move sm
                            join stock_picking sp on
                                sm.picking_id = sp.id
                            join stock_location sl on
                                sm.location_dest_id = sl.id
                            join account_move am on
                                sm.id = am.stock_move_id
                            join account_move_line aml on
                                am.id = aml.move_id
                            join product_product pp on
                                aml.product_id = pp.id
                            join product_template pt on
                                pp.product_tmpl_id = pt.id
                            join account_account aa on aml.account_id = aa.id
                            join product_category pc on
                                pt.categ_id = pc.id
                            join ir_property ip on
                                ip.res_id = 'product.category,' || pt.categ_id
                                and ip."name" = 'property_stock_valuation_account_id'
                                and ip.company_id = {company_id}
                                and ip.value_reference = 'account.account,' || aa.id
                    
                            where
                                am.state = 'posted'
                                and am.date >= '{from_date}' and am.date <= '{to_date} 23:59:59'
                                and am.company_id = {company_id}
                    
                        
                            union 
                            
                            select
                                pp.id product_id,
                                - aml.credit amount,
                                am.name
                            from
                                stock_move sm
                            join stock_picking sp on
                                sm.picking_id = sp.id
                            join account_move am on
                                sm.id = am.stock_move_id
                            join stock_location sl on
                                sm.location_id = sl.id
                            join account_move_line aml on
                                am.id = aml.move_id
                            join product_product pp on
                                aml.product_id = pp.id
                            join product_template pt on
                                pp.product_tmpl_id = pt.id
                            join account_account aa on aml.account_id = aa.id
                            join product_category pc on
                                pt.categ_id = pc.id
                            join ir_property ip on
                                ip.res_id = 'product.category,' || pt.categ_id
                                and ip."name" = 'property_stock_valuation_account_id'
                                and ip.company_id = {company_id}
                                and ip.value_reference = 'account.account,' || aa.id
                            join stock_move sm2 on sm.origin_returned_move_id = sm2.id
                            
                            where
                                am.state = 'posted'
                                and am.date >= '{from_date}' and am.date <= '{to_date} 23:59:59'
                                and am.company_id = {company_id}
                                
                        ) as mt
                        group by mt.product_id
                        
                        union 
                        
                        select product_id, sum(amount) amount from (
                            select
                                pp.id product_id,
                                sum(aml.debit) - sum(aml.credit) amount
                    
                        
                            from account_move am
                            join account_journal aj on am.journal_id = aj.id
                            join account_move_line aml on
                            am.id = aml.move_id
                            join product_product pp on
                            aml.product_id = pp.id
                            join product_template pt on
                            pp.product_tmpl_id = pt.id
                            join account_account aa on
                            aml.account_id = aa.id
                            left join purchase_order_line pol on aml.purchase_line_id = pol.id
                            left join purchase_order po on pol.order_id = po.id and (po.is_return is null or po.is_return is false)
                            
                            where 
                            (aa.code like '1562%' or aa.code like '3319%') 
                            and am.state = 'posted'
                            and am.payment_state != 'reversed'
                            and am.date >= '{from_date}' and am.date <= '{to_date} 23:59:59'
                            and am.company_id = {company_id}
                            and am.stock_move_id is null
                            and am.id not in (
                            select am2.id from account_move am 
                                join account_move_line aml on am.id = aml.move_id 
                                join purchase_order_line pol on pol.id = aml.purchase_line_id 
                                join purchase_order po on po.id = pol.order_id 
                                join account_move am2 on am.name = split_part(am2.ref, ' - ', 1)
                            where po.is_return is true 
                            and aml.company_id = {company_id}
                            and aml.date >= '{from_date}' and aml.date <= '{to_date} 23:59:59'
                            )
                            group by
                            pp.id
                        
                        union 
                        
                            select
                            pp.id product_id,
                            - (sum(aml.credit) - sum(aml.debit)) amount
                            
                            from account_move am
                            join account_journal aj on am.journal_id = aj.id
                            join account_move_line aml on
                            am.id = aml.move_id
                            join product_product pp on
                            aml.product_id = pp.id
                            join product_template pt on
                            pp.product_tmpl_id = pt.id
                            join account_account aa on
                            aml.account_id = aa.id
                            join stock_move sm on sm.id = am.stock_move_id 
                            join stock_picking sp on sm.picking_id = sp.id
                            
                            where 
                            (aa.code like '1562%' or aa.code like '3319%') 
                            and am.state = 'posted'
                            and am.payment_state != 'reversed'
                            and am.date >= '{from_date}' and am.date <= '{to_date} 23:59:59'
                            and am.company_id = {company_id}
                            and am.x_entry_types != 'entry_material'
                            
                            group by
                            pp.id
                        )
                        mt group by product_id
                    ) amount_period group by product_id
                ),
                amount_first as (
                    select product_id, sum(amount) amount from (
                        select
                            pp.id product_id,
                            sum(aml.debit) - sum(aml.credit) amount
                        
                        from account_move am
                        join account_move_line aml on
                        am.id = aml.move_id
                        join product_product pp on
                        aml.product_id = pp.id
                        join product_template pt on
                        pp.product_tmpl_id = pt.id
                        join account_account aa on aml.account_id = aa.id
                        join product_category pc on
                            pt.categ_id = pc.id
                        join ir_property ip on
                            ip.res_id = 'product.category,' || pt.categ_id
                            and ip."name" = 'property_stock_valuation_account_id'
                            and ip.company_id = {company_id}
                            and ip.value_reference = 'account.account,' || aa.id
                        
                        where 
                        am.invoice_type in ('increase', 'decrease') 
                        and aa.code like '3319%' 
                        and am.state = 'posted'
                        and am.payment_state != 'reversed'
                        and am.date < '{from_date}'
                        and am.company_id = {company_id}
                        
                        group by
                        pp.id
                    
                        union
                        select
                            product_id,
                            sum(amount)
                        from
                            (
                            select
                                pp.id product_id,
                                aml.debit amount,
                                am.name
                            from
                                stock_move sm
                            join stock_picking sp on
                                sm.picking_id = sp.id
                            join stock_location sl on
                                sm.location_dest_id = sl.id
                            join account_move am on
                                sm.id = am.stock_move_id
                            join account_move_line aml on
                                am.id = aml.move_id
                            join product_product pp on
                                aml.product_id = pp.id
                            join product_template pt on
                                pp.product_tmpl_id = pt.id
                            join account_account aa on aml.account_id = aa.id
                            join product_category pc on
                                pt.categ_id = pc.id
                            join ir_property ip on
                                ip.res_id = 'product.category,' || pt.categ_id
                                and ip."name" = 'property_stock_valuation_account_id'
                                and ip.company_id = {company_id}
                                and ip.value_reference = 'account.account,' || aa.id
                    
                            where
                                am.state = 'posted'
                                and am.date < '{from_date}'
                                and am.company_id = {company_id}
                    
                        
                            union 
                            
                            select
                                pp.id product_id,
                                - aml.credit amount,
                                am.name
                            from
                                stock_move sm
                            join stock_picking sp on
                                sm.picking_id = sp.id
                            join account_move am on
                                sm.id = am.stock_move_id
                            join stock_location sl on
                                sm.location_id = sl.id
                            join account_move_line aml on
                                am.id = aml.move_id
                            join product_product pp on
                                aml.product_id = pp.id
                            join product_template pt on
                                pp.product_tmpl_id = pt.id
                            join account_account aa on aml.account_id = aa.id
                            join product_category pc on
                                pt.categ_id = pc.id
                            join ir_property ip on
                                ip.res_id = 'product.category,' || pt.categ_id
                                and ip."name" = 'property_stock_valuation_account_id'
                                and ip.company_id = {company_id}
                                and ip.value_reference = 'account.account,' || aa.id
                            join stock_move sm2 on sm.origin_returned_move_id = sm2.id
                            
                            where
                                am.state = 'posted'
                                and am.date < '{from_date}'
                                and am.company_id = {company_id}
                                
                        ) as mt
                        group by mt.product_id
                        
                        union 
                        
                        select product_id, sum(amount) amount from (
                            select
                                pp.id product_id,
                                sum(aml.debit) - sum(aml.credit) amount
                    
                        
                            from account_move am
                            join account_journal aj on am.journal_id = aj.id
                            join account_move_line aml on
                            am.id = aml.move_id
                            join product_product pp on
                            aml.product_id = pp.id
                            join product_template pt on
                            pp.product_tmpl_id = pt.id
                            join account_account aa on
                            aml.account_id = aa.id
                            left join purchase_order_line pol on aml.purchase_line_id = pol.id
                            left join purchase_order po on pol.order_id = po.id and (po.is_return is null or po.is_return is false)
                            
                            where 
                            (aa.code like '1562%' or aa.code like '3319%') 
                            and am.state = 'posted'
                            and am.payment_state != 'reversed'
                            and am.date < '{from_date}'
                            and am.company_id = {company_id}
                            and am.stock_move_id is null
                            and am.id not in (
                            select am2.id from account_move am 
                                join account_move_line aml on am.id = aml.move_id 
                                join purchase_order_line pol on pol.id = aml.purchase_line_id 
                                join purchase_order po on po.id = pol.order_id 
                                join account_move am2 on am.name = split_part(am2.ref, ' - ', 1)
                            where po.is_return is true 
                            and aml.company_id = {company_id}
                            and am.date < '{from_date}'
                            )
                            group by
                            pp.id
                        
                        union 
                        
                            select
                            pp.id product_id,
                            - (sum(aml.credit) - sum(aml.debit)) amount
                            
                            from account_move am
                            join account_journal aj on am.journal_id = aj.id
                            join account_move_line aml on
                            am.id = aml.move_id
                            join product_product pp on
                            aml.product_id = pp.id
                            join product_template pt on
                            pp.product_tmpl_id = pt.id
                            join account_account aa on
                            aml.account_id = aa.id
                            join stock_move sm on sm.id = am.stock_move_id 
                            join stock_picking sp on sm.picking_id = sp.id
                            
                            where 
                            (aa.code like '1562%' or aa.code like '3319%') 
                            and am.state = 'posted'
                            and am.payment_state != 'reversed'
                            and am.date < '{from_date}'
                            and am.company_id = {company_id}
                            and am.x_entry_types != 'entry_material'
                            
                            group by
                            pp.id
                        )
                        mt group by product_id
                    ) amount_first group by product_id
                )
                
                select 
                    {parent_id} parent_id,
                    pp.id product_id,
                    qif.qty_done qty_begin_period,
                    qiip.qty_done qty_in_period,
                    qiop.qty_done qty_out_period,
                    ap.amount amount_period,
                    af.amount amount_begin_period
                    
                from product_product pp 
                left join product_template pt on pp.product_tmpl_id = pt.id
                left join quantity_inventory_first qif on
                    pp.id = qif.product_id
                left join quantity_inventory_in_period qiip on
                    pp.id = qiip.product_id
                left join quantity_inventory_out_period qiop on
                    pp.id = qiop.product_id
                left join return_in_period rip on
                    pp.id = rip.product_id
                left join amount_period ap on
                    pp.id = ap.product_id
                left join amount_first af on
                    pp.id = af.product_id
                where pt.detailed_type = 'product'
    """

    def action_product_inventory(self):
        sql = self._sql_string_inv().format(
            parent_id=self.id,
            from_date=self.from_date,
            to_date=self.to_date,
            company_id=self.env.company.id)
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        inv_line = self.inv_lines.create(data)
        self.state = 'done'

    def action_view_product_inventory(self):
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_stock_report.product_inventory_line_action')
        action['domain'] = [('parent_id', '=', self.id)]
        return action


class ProductInventoryLine(models.Model):
    _name = 'product.inventory.by.period.line'
    _description = 'Tồn kho sản phẩm theo kỳ chi tiết'
    _rec_name = 'product_id'

    parent_id = fields.Many2one('product.inventory.by.period', string='Kỳ chốt tồn', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    qty_begin_period = fields.Float(string='Tồn đầu')
    qty_in_period = fields.Float(string='Nhập trong kỳ')
    qty_out_period = fields.Float(string='Xuất trong kỳ')
    qty_product = fields.Float(string='Tồn cuối', compute='_compute_qty_product', store=True)
    amount_begin_period = fields.Float(string='Giá trị đầu kỳ', digits=(16, 2))
    amount_period = fields.Float(string='Giá trị nhập trong kỳ', digits=(16, 2))
    amount_product = fields.Float(string='Đơn giá bình quân cuối kỳ', compute='_compute_amount_product', store=True, digits=(16, 2))
    date = fields.Date(string='Ngày chốt tồn', related='parent_id.to_date', store=True)

    @api.depends('qty_begin_period', 'qty_in_period', 'amount_begin_period', 'amount_period')
    def _compute_amount_product(self):
        for rec in self:
            if (rec.qty_begin_period + rec.qty_in_period) != 0:
                rec.amount_product = (rec.amount_period + rec.amount_begin_period) / (rec.qty_begin_period + rec.qty_in_period)
            else:
                rec.amount_product = 0

    @api.depends('qty_begin_period', 'qty_in_period')
    def _compute_qty_product(self):
        for rec in self:
            rec.qty_product = (rec.qty_begin_period + rec.qty_in_period) - rec.qty_out_period
