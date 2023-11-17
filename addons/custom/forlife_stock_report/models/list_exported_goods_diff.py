from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class CalculateFinalValue(models.Model):
    _inherit = 'calculate.final.value'
    _description = 'Tính giá trị cuối kỳ'

    goods_diff_lines = fields.One2many('list.exported.goods.diff', 'parent_id', string='Bảng kê chênh lệch')
    goods_diff_count = fields.Float(compute='compute_goods_diff_lines')

    @api.depends('goods_diff_lines')
    def compute_goods_diff_lines(self):
        for rec in self:
            rec.goods_diff_count = len(rec.goods_diff_lines)

    def _sql_string_good_diff(self):
        return """
            with list_product as (
                select 
                    {parent_id} parent_id,
                    pp.id product_id,
                    aa.id account_id,
                    '' production_code,
                    case when oc.code is not null then concat('[', oc.code, '] ', oc.name) else '' end occasion_code,
                    case when aaa.code is not null then concat('[', aaa.code, '] ', aaa.name->>'vi_VN') else '' end account_analytic,
                    case when aa2.code is not null then concat('[', aa2.code, '] ', aa2.name) else '' end asset_code,
                    case when sm.product_production_id is not null then sm.product_production_id
                    else spls.product_split_id end product_end_id,
                    case 
	                    when spls.quantity > 0 then spls.quantity
                        when (pibpl.qty_product > 0) then sm.quantity_done
                        when (pibpl.qty_product = 0 and (sp.x_is_check_return is false or sp.x_is_check_return is null)) then sm.quantity_done
                        when pibpl.qty_product = 0 and sp.x_is_check_return is true then 0
                        else sm.quantity_done
                    end qty,
                    case when spls.product_split_id is not null then (spls.quantity * aml.debit) / sm.quantity_done
                    else aml.debit end amount_export
                from stock_move sm 
                join account_move am on am.stock_move_id = sm.id and (am.end_period_entry is null or am.end_period_entry is false)
                join account_move_line aml on am.id = aml.move_id 
                join product_product pp on pp.id = aml.product_id 
                join product_template pt on pp.product_tmpl_id = pt.id
                join product_category pc on pt.categ_id = pc.id
                join product_category_type cpt on pc.category_type_id = cpt.id
                join account_account aa on aml.account_id = aa.id
                join stock_picking sp on sm.picking_id = sp.id
                join stock_location sl on sm.location_id = sl.id and sl."usage" = 'internal'
                left join split_product sp2 on sp.split_product_id = sp2.id
                left join split_product_line_sub spls on sp2.id = spls.parent_id 
                left join occasion_code oc on oc.id = sm.occasion_code_id 
                left join account_analytic_account aaa on sm.account_analytic_id = aaa.id
                left join assets_assets aa2 on aa2.id = sm.ref_asset
                left join forlife_production fp on sm.work_production = fp.id or sm.work_to = fp.id
                left join product_inventory_by_period_line pibpl on pp.id = pibpl.product_id and pibpl.date = '{date_inv}'
                
                where 
                aml.debit > 0 
                and sm.company_id = {company_id} 
                and sm.date + interval '7 hours' >= '{from_date}' and sm.date + interval '7 hours' <= '{to_date} 23:59:59'
                and sm.state = 'done'
                and (sp.x_is_check_return is false or sp.x_is_check_return is null)
                and cpt.code = {category_type}
            )

            select 
            lp.parent_id parent_id, 
            lp.product_id product_id, 
            lp.account_id account_id, 
            lp.production_code production_code, 
            lp.occasion_code occasion_code, 
            lp.account_analytic account_analytic, 
            lp.asset_code asset_code, 
            lp.product_end_id product_end_id,
            sum(lp.qty) qty,
            sum(lp.amount_export) amount_export,
            round(max(pibcf.amount_product) * sum(lp.qty)) amount_avg,
            round(sum(lp.amount_export) - (max(pibcf.amount_product) * sum(lp.qty))) amount_diff
            from list_product lp left join product_inventory_by_calculate_final pibcf on 
            lp.product_id = pibcf.product_id and pibcf.parent_id = {parent_id}
            
            where lp.qty <> 0
            
            group by
            lp.parent_id, 
            lp.product_id, 
            lp.account_id, 
            lp.production_code, 
            lp.occasion_code, 
            lp.account_analytic, 
            lp.asset_code, 
            lp.product_end_id
        """

    def get_data_diff_value(self):
        if self.state not in ('step1', 'step2'):
            raise ValidationError('Bản chỉ có thể thực hiện khi hoàn thành tính đơn giá bình quân sản phẩm')
        self.goods_diff_lines.unlink()
        query = self._sql_string_good_diff().format(
            company_id=self.env.company.id,
            from_date=self.from_date,
            to_date=self.to_date,
            date_inv=self.from_date - timedelta(days=1),
            parent_id=self.id,
            category_type="any(array['2', '3'])" if self.category_type_id == 'npl_ccdc' else "any(array['1'])"
        )
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        create_vals = []
        for d in data:
            if d['amount_diff'] == 0:
                continue
            create_vals.append(d)
        self.env['list.exported.goods.diff'].create(create_vals)
        self.state = 'step2'

class ListExportedGoodsDiff(models.Model):
    _name = 'list.exported.goods.diff'
    _description = 'Bảng kê chênh lệch tính chất xuất'

    parent_id = fields.Many2one('calculate.final.value', string='Kỳ tính', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm nguồn')
    account_id = fields.Many2one('account.account', string='Tài khoản')
    production_code = fields.Char(string='Lệnh sản xuất')
    occasion_code = fields.Char(string='Mã vụ việc')
    account_analytic = fields.Char(string='Trung tâm chi phí')
    asset_code = fields.Char(string='Mã tai sản')
    product_end_id = fields.Many2one('product.product', string='Sản phẩm đích')
    qty = fields.Float(string='Số lượng')
    amount_export = fields.Float(string='Giá trị xuất')
    amount_avg = fields.Float(string='Giá trị bình quân')
    amount_diff = fields.Float(string='Chênh lệch', store=True)

    @api.depends('amount_export', 'amount_avg')
    def compute_amount_diff(self):
        for rec in self:
            rec.amount_diff = rec.amount_export - rec.amount_avg

