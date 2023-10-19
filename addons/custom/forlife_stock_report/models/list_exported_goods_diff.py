from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class CalculateFinalValue(models.Model):
    _inherit = 'calculate.final.value'
    _description = 'Tính giá trị cuối kỳ'

    goods_diff_lines = fields.One2many('list.exported.goods.diff', 'parent_id', string='Bảng kê chênh lệch')

    def _sql_string_good_diff(self):
        return """
            with list_product as (
                select 
                    {parent_id} parent_id,
                    pp.id product_id,
                    aa.id account_id,
                    '' production_code,
                    oc.code occasion_code,
                    aaa.code account_analytic,
                    aa2.code asset_code,
                    spls.product_split_id product_end_id,
                    sm.quantity_done qty,
                    aml.debit amount_export
                from stock_move sm 

                left join stock_picking sp on sm.picking_id = sp.id 
                left join split_product sp2 on sp.split_product_id = sp2.id
                left join split_product_line_sub spls on sp2.id = spls.parent_id 
                left join stock_location sl on sl.id = sm.location_id and sl."usage" = 'internal'
                left join product_product pp on sm.product_id = pp.id
                left join product_template pt on pp.product_tmpl_id = pt.id
                left join product_category pc on pt.categ_id = pc.id
                left join product_category_type cpt on pc.category_type_id = cpt.id
                left join account_move am on sm.id = am.stock_move_id and (am.end_period_entry is null or am.end_period_entry is false)
                left join account_move_line aml on aml.move_id = am.id
                left join account_account aa on aml.account_id = aa.id
                left join occasion_code oc on oc.id = sm.occasion_code_id 
                left join account_analytic_account aaa on sm.account_analytic_id = aaa.id
                left join assets_assets aa2 on aa2.id = sm.ref_asset
                
                where 
                aml.debit > 0 
                and sm.company_id = {company_id} 
                and sm.date + interval '7 hours' >= '{from_date}' and sm.date + interval '7 hours' <= '{to_date} 23:59:59'
                and sm.state = 'done'
                and (sp.x_is_check_return is false or sp.x_is_check_return is null)
                and cpt.code = {category_type}

                union 

                select
                    {parent_id} parent_id,
                    pp.id product_id,
                    aa.id account_id,
                    fp.code production_code,
                    oc.code occasion_code,
                    aaa.code account_analytic,
                    aa2.code asset_code,
                    fpm.product_id product_end_id,
                    (fpm.total * sm.quantity_done) qty,
                    (sm2.price_unit * sm.quantity_done) amount_export
                from stock_move sm 

                join stock_picking sp on sm.picking_id = sp.id
                join stock_picking sp2 on sp.picking_outgoing_id = sp2.id
                join stock_move sm2 on sp2.id = sm2.picking_id 
                join forlife_production fp on sm2.work_production = fp.id
                join forlife_production_finished_product fpfp on fpfp.forlife_production_id = fp.id
                join forlife_production_material fpm on fpfp.id = fpm.forlife_production_id 
                join account_move am on sm.id = am.stock_move_id and (am.end_period_entry is null or am.end_period_entry is false)
                join account_move_line aml on aml.move_id = am.id
                join account_account aa on aml.account_id = aa.id
                left join product_product pp on sm.product_id = pp.id
                left join product_template pt on pp.product_tmpl_id = pt.id
                left join product_category pc on pt.categ_id = pc.id
                left join product_category_type cpt on pc.category_type_id = cpt.id
                left join occasion_code oc on oc.id = sm.occasion_code_id 
                left join account_analytic_account aaa on sm.account_analytic_id = aaa.id
                left join assets_assets aa2 on aa2.id = sm.ref_asset

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
            sum(pibcf.amount_product) amount_avg 
            from list_product lp left join product_inventory_by_calculate_final pibcf on 
            lp.product_id = pibcf.product_id and pibcf.parent_id = {parent_id}
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
        if self.state != 'step1':
            raise ValidationError('Bản chỉ có thể thực hiện khi hoàn thành tính đơn giá bình quân sản phẩm')
        self.goods_diff_lines.unlink()
        query = self._sql_string_good_diff().format(
            company_id=self.env.company.id,
            from_date=self.from_date,
            to_date=self.to_date,
            parent_id=self.id,
            category_type="any(array['2', '3'])" if self.category_type_id == 'npl_ccdc' else "any(array['1'])"
        )
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        self.env['list.exported.goods.diff'].create(data)
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
    amount_diff = fields.Float(string='Chênh lệch', compute='compute_amount_diff', store=True)

    @api.depends('amount_export', 'amount_avg')
    def compute_amount_diff(self):
        for rec in self:
            rec.amount_diff = rec.amount_export - rec.amount_avg

