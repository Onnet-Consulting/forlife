# -*- coding:utf-8 -*-
from forlife_report.wizard.report_base import format_date_query
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import copy
from datetime import datetime, timedelta, date

TITLES = [
    'STT',
    'Kho',
    'Địa điểm',
    'Mã SP',
    'Tên SP',
    'Size',
    'Màu',
    'Đơn vị',
    'Số lượng',
    'Đơn giá',
    'Thuế suất',
    'Thuế GTGT',
    'Doanh thu bán hàng',
    'Giảm trừ doanh thu',
    'Khuyến mại bán hàng',
    'Tổng thanh toán',
    'Nhóm hàng',
    'Dòng hàng',
    'Kết cấu',
    'Mã loại sp',
    'Kênh bán',
]

years = [(str(year), str(year)) for year in range(date.today().year, date.today().year + 100)]


class ReportNum30(models.TransientModel):
    _name = 'report.num33'
    _inherit = 'report.base'
    _description = 'Báo cáo doanh thu sản phẩm'

    @api.model
    def _get_default_year(self):
        return fields.Date.today().year

    @api.model
    def _get_default_month(self):
        return self.env['month.data'].search([('code', '=', str(fields.Date.today().month))])

    date_from = fields.Datetime(string='Từ ngày', required=True)
    date_to = fields.Datetime(string='Đến ngày', required=True)
    product_count = fields.Integer('Số lượng sản phẩm', compute='_compute_value')
    product_ids = fields.Many2many('product.product', string='Sản phẩm',
                                   domain="['|', ('detailed_type', '=', 'product'), '&', ('detailed_type', '=', 'service'), ('voucher', '=', True)]")
    warehouse_type_id = fields.Many2one('stock.warehouse.type', string='Loại kho', required=True)
    warehouse_count = fields.Integer('Số kho', compute='_compute_value')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Kho')
    is_get_price_unit = fields.Boolean('Lấy đơn giá', default=True)
    is_with_tax = fields.Boolean('Bao gồm thuế', default=True)
    sale_channels = fields.Selection([
        ('is_pos_order', 'Đơn bán hàng POS'),
        ('is_wholesale', 'Đơn bán buôn'),
        ('is_ecommerce', 'Đơn hàng TMĐT'),
        ('is_inter_company', 'Đơn bán liên công ty'),
    ], string='Kênh bán', required=True)
    brand_id = fields.Many2one('product.category', string='Thương hiệu', domain=[('parent_id', '=', False)])
    group_id = fields.Many2one('product.category', string='Nhóm hàng',
                               domain="[('parent_id', '=', brand_id), ('parent_id', '!=', False)]")
    line_id = fields.Many2one('product.category', string='Dòng hàng',
                              domain="[('parent_id', '=', group_id), ('parent_id', '!=', False)]")
    structure_id = fields.Many2one('product.category', string='Kết cấu',
                                   domain="[('parent_id', '=', line_id), ('parent_id', '!=', False)]")
    size = fields.Many2one('product.attribute.value', domain=[('attribute_id.attrs_code', '=', 'AT006')], string='Size')
    color = fields.Many2one('product.attribute.value', domain=[('attribute_id.attrs_code', '=', 'AT004')],
                            string='Color')

    @api.depends('product_ids', 'warehouse_ids')
    def _compute_value(self):
        for line in self:
            line.product_count = len(line.product_ids)
            line.warehouse_count = len(line.warehouse_ids)

    def btn_choice_values(self):
        action = self.env["ir.actions.actions"]._for_xml_id(f"forlife_report.{self._context.get('action_xml_id')}")
        action['res_id'] = self.id
        action['context'] = self._context
        return action

    @api.onchange('warehouse_type_id')
    def onchange_warehouse_type_id(self):
        self.warehouse_ids = self.warehouse_ids.filtered(lambda f: f.whs_type.id == self.warehouse_type_id.id)

    @api.constrains('year')
    def check_year(self):
        for record in self:
            if record.year == 0:
                raise ValidationError('Năm không hợp lệ')

    def _get_query(self):
        self.ensure_one()
        attr_value = self.env['res.utility'].get_attribute_code_config()
        tz_offset = self.tz_offset
        query = f"""
            with attrs as (select
                product_id,
                STRING_AGG(distinct color, ', ') as color,
                STRING_AGG(distinct size, ', ') as size
            from
                (
                select
                    pp.id as product_id,
                    case 
                        when pa.attrs_code = '{attr_value.get('mau_sac', '')}' then coalesce(pav.name::json->>'vi_VN',
                        pav.name::json->>'en_US')
                    end as color,
                    case 
                        when pa.attrs_code = '{attr_value.get('size', '')}' then coalesce(pav.name::json->>'vi_VN',
                        pav.name::json->>'en_US')
                    end as size
                from
                    product_template_attribute_line ptal
                left join product_product pp on
                    pp.product_tmpl_id = ptal.product_tmpl_id
                left join product_attribute_value_product_template_attribute_line_rel rel on
                    rel.product_template_attribute_line_id = ptal.id
                left join product_attribute pa on
                    ptal.attribute_id = pa.id
                left join product_attribute_value pav on
                    pav.id = rel.product_attribute_value_id
                where
                    pa.attrs_code is not null
                group by
                    pp.id,
                    pa.attrs_code,
                    pav.name
                ) mt
            group by
                product_id)
        """
        if self.sale_channels == 'is_pos_order':
            query += f"""
                select
                    por.warehouse_name,
                    por.warehouse_id,
                    por.location_name,
                    por.barcode,
                    por.product_name,
                    attrs.color,
                    attrs.size,
                    por.uom_name,
                    SUM (por.qty) as qty,
                    {'por.price_tax,' if self.is_get_price_unit else ''}
                    por.tax_rate,
                    SUM ( por.tax_amount - por.tax_discount ) as tax_amount,
                    SUM (por.revenues_511) as revenues_511,
                    SUM (por.discounted_amount) as discount_amount,
                    SUM (por.revenue_deduction) as revenue_deduction,
                    SUM (por.price_subtotal_incl) as price_subtotal_incl,
                    por.product_group,
                    por.product_line,
                    por.texture_name,
                    por.warehouse_type,
                    por.valuation_account,
                    por.gift
                from
                    (
                    select
                        pos.date_order,
                        pol.order_id,
                        pol.ID as order_line_id,
                        pol.product_id,
                        whs.warehouse_name,
                        whs.warehouse_id,
                        whs.location_name,
                        p1.barcode,
                        p1.product_name,
                        p1.uom_name,
                        pol.qty,
                        case
                            when tax.tax_rate is null then pol.original_price
                            else
                                round(pol.original_price / ( 1 + tax.tax_rate ),
                            0 )
                        end as price_tax,
                        case
                            when tax.tax_rate is null then 0
                            else tax.tax_rate
                        end as tax_rate,
                        case
                            when tax.tax_rate is null then 0
                            when pol.price_unit = 0 then 0
                            else round(( pol.qty * pol.original_price * tax.tax_rate ) / ( 1 + tax.tax_rate ))
                        end as tax_amount,
                        case
                            when pol.price_unit = 0 then 0
                            when pol.discount = 100 then 0
                            when dis.revenue is null then psi.price_subtotal
                            when tax.tax_rate is null then psi.price_subtotal - dis.revenue
                            else psi.price_subtotal - round( dis.revenue / ( 1 + tax.tax_rate ) )
                        end as revenues_511,
                        case
                            when (pol.is_reward_line = true
                            and tax.tax_rate is not null) then ROUNd(dis.revenue / ( 1 + tax.tax_rate ))
                            when dis.revenue is null then 0
                            when tax.tax_rate is null then dis.revenue
                            else ROUNd(dis.revenue / ( 1 + tax.tax_rate ))
                        end as discounted_amount,
                        case
                            when dis.expenses is null then 0
                            else dis.expenses
                        end as revenue_deduction,
                        case
                        when pol.price_unit = 0 then 0
                            when tax.tax_rate is null then 0
                            else ROUND((coalesce(dis.expenses,
                            0)) * tax.tax_rate / (1 + tax.tax_rate))
                        end as tax_discount,
                        psi.price_subtotal_incl,
                        p1.product_group,
                        p1.product_line,
                        p1.texture_name,
                        p1.detailed_type,
                        whs.warehouse_type,
                        p1.valuation_account,
                        case
                            when ( pol.is_reward_line = true
                            and pol.with_purchase_condition = true ) then
                                'conditional'
                            when ( pol.is_reward_line = true
                            and pol.with_purchase_condition = false ) then
                                'unconditional'
                            else ''
                        end as gift
                    from
                        pos_order_line pol
                    left join pos_order pos on
                        pos.ID = pol.order_id
                    left join (
                        select
                            pos_order_line_id,
                            SUM (
                                case
                                when type = 'point' then recipe * 1000
                                when type = 'card' then round(recipe)
                                when type = 'product_defective' then round(recipe)
                                when recipe is null then 0
                                else 0
                            end 
                            ) as expenses,
                            SUM (
                                case
                                when type = 'point' then 0
                                when type = 'card' then 0
                                when discounted_amount is null then 0
                                else coalesce ( discounted_amount,
                                0 )
                            end 
                            ) as revenue
                        from
                            pos_order_line_discount_details
                        where
                            "type" <> 'handle'
                        group by
                            pos_order_line_id 
                                        ) as dis on
                        dis.pos_order_line_id = pol."id"
                    left join (
                        select
                            act.ID,
                            atr.pos_order_line_id,
                            {'round( act.amount / 100,2 )' if not self.is_with_tax else 0} as tax_rate
                        from
                            account_tax act
                        left join account_tax_pos_order_line_rel atr on
                            atr.account_tax_id = act.ID
                        where
                            act.type_tax_use = 'sale') as tax on
                        tax.pos_order_line_id = pol."id"
                    left join (
                        select
                            cl.ID as order_line_id,
                            cl.incl_1 + cl.incl_2 as price_subtotal_incl,
                            cl.price_subtotal
                        from
                            (
                            select
                                pl1.ID,
                                pl1.price_subtotal_incl as incl_1,
                                SUM ( case
                                    when pl2.price_subtotal_incl is null then 0
                                    else pl2.price_subtotal_incl
                                end ) as incl_2,
                                pl1.price_subtotal
                            from
                                pos_order_line pl1
                            left join pos_order_line pl2 on
                                pl1.ID = pl2.product_src_id
                            where
                                pl1.product_src_id is null
                            group by
                                pl1.ID,
                                pl1.price_subtotal_incl,
                                pl1.price_subtotal 
                                                ) as cl 
                                        ) as psi on
                        psi.order_line_id = pol."id"
                    left join (
                        select
                            spk.id as picking_id,
                            stm.product_id,
                            spk.pos_order_id,
                            pkt.default_location_src_id as location_id,
                            pkt.warehouse_id,
                            stw."name" as warehouse_name,
                            concat ( stw."name",
                            '/',
                            loc."name" ) as location_name,
                            wht."name" as warehouse_type
                        from
                            stock_move stm
                        left join stock_picking spk on
                            spk."id" = stm.picking_id
                        left join stock_picking_type pkt on
                            pkt."id" = spk.picking_type_id
                        left join stock_warehouse stw on
                            stw."id" = pkt.warehouse_id
                        left join stock_location loc on
                            loc."id" = pkt.default_location_src_id
                        left join stock_warehouse_type wht on
                            wht."id" = stw.whs_type 
                                        ) as whs on
                        (whs.pos_order_id = poL.order_id
                            and whs.product_id = pol.product_id)
                    left join (
                        select
                            prd."id" as product_id,
                            coalesce ( uom.NAME :: JSON ->> 'vi_VN',
                            uom.NAME :: JSON ->> 'en_US' ) :: text as uom_name,
                            prt.detailed_type,
                            prt.voucher,
                            coalesce ( prt.NAME :: JSON ->> 'vi_VN',
                            prt.NAME :: JSON ->> 'en_US' ) :: text as product_name,
                            split_part( ctg.complete_name,
                            ' / ',
                            2 ) as product_group,
                            split_part( ctg.complete_name,
                            ' / ',
                            3 ) as product_line,
                            split_part( ctg.complete_name,
                            ' / ',
                            4 ) as texture_name,
                            prt.barcode,
                            aa.code as valuation_account
                        from
                            product_product prd
                        left join product_template prt on
                            prt.ID = prd.product_tmpl_id
                        left join product_category ctg on
                            ctg."id" = prt.categ_id
                        left join uom_uom uom on
                            uom.ID = prt.uom_id 
                        left join ir_property ip on ip.res_id = 'product.category,' || prt.categ_id AND ip."name" = 'property_stock_valuation_account_id' and ip.company_id = {self.env.company.id}
                        left join account_account aa on 'account.account,' || aa.id = ip.value_reference
                        ) as p1 on
                        p1.product_id = pol.product_id
                    where
                        ( P1.detailed_type = 'product'
                            or ( P1.detailed_type = 'service'
                                and P1.voucher = true ) )
                        and POL.qty <> 0
                
                        ) as por
                left join attrs on attrs.product_id = por.product_id
                where
                    1=1
            """
        else:
            query += f"""
                select
                    por.warehouse_name,
                    por.location_name,
                    por.barcode,
                    por.product_name,
                    attrs.color,
                    attrs.size,
                    por.uom_name,
                    SUM (por.quantity) as qty,
                    {'por.price_tax,' if self.is_get_price_unit else ''}
                    por.tax_rate,
                    SUM (por.tax_amount) as tax_amount,
                    sum (por.price_subtotal) as revenues_511 ,
                    SUM (por.discount_amount) as discount_amount,
                    SUM (por.revenue_deduction) as revenue_deduction,
                    SUM (por.price_subtotal_incl) as price_subtotal_incl,
                    por.product_group,
                    por.product_line,
                    por.texture_name,
                    por.warehouse_type,
                    por.valuation_account,
                    por.gift
                from
                    (
                    select
                        acl."date" as date_order,
                        sol.order_id,
                        sli.invoice_line_id,
                        acm."id" as account_move_id,
                        whs.warehouse_id,
                        whs.warehouse_name,
                        sol.x_location_id,
                        whs.location_name,
                        sod.source_record as is_nhanhvn,
                        acl.product_id,
                        p1.product_name,
                        p1.uom_name,
                        p1.barcode,
                        case
                            when acm.move_type = 'out_refund' then
                                acl.quantity * - 1
                            else acl.quantity
                        end as quantity,
                        acl.price_unit as price_tax,
                        {'''case
                            when atx.amount is null then 0
                            else
                                ROUND(atx.amount)
                        end''' if not self.is_with_tax else 0} as tax_rate,
                        case
                            when acl.tax_amount is null then 0
                            when acl.tax_amount is not null
                            and amp."value" is null then acl.tax_amount
                            else acl.tax_amount + (amp."value" /(1 + atx.amount))
                        end as tax_amount,
                        acl.discount,
                        case
                            when acm.move_type = 'out_refund' then
                                ROUND( ( acl.quantity * acl.price_unit * acl.discount / 100 / 1.1 ) :: numeric ) * - 1
                            else ROUND( ( acl.quantity * acl.price_unit * acl.discount / 100 / 1.1 ) :: numeric )
                        end as discount_amount,
                        case
                            when amp."value" is null then
                                0
                            else amp."value"
                        end as revenue_deduction,
                        case
                            when acm.move_type = 'out_refund' then
                                acl.price_subtotal * - 1
                            else acl.price_subtotal
                        end as price_subtotal,
                        case
                            when ( acm.move_type = 'out_refund'
                            and acl.tax_amount is null
                            and amp."value" is null ) then
                                acl.price_subtotal * - 1
                            when ( acm.move_type = 'out_refund'
                            and acl.tax_amount is not null
                            and amp."value" is null ) then
                                ( acl.price_subtotal + acl.tax_amount ) * - 1
                            when ( acm.move_type = 'out_refund'
                            and acl.tax_amount is null
                            and amp."value" is not null ) then
                                ( acl.price_subtotal - amp."value" ) * - 1
                            when ( acm.move_type = 'out_refund'
                            and acl.tax_amount is not null
                            and amp."value" is not null ) then
                                ( acl.price_subtotal - amp."value" + acl.tax_amount ) * - 1
                            when ( acm.move_type <> 'out_refund'
                            and acl.tax_amount is null
                            and amp."value" is null ) then
                                acl.price_subtotal
                            when ( acm.move_type <> 'out_refund'
                            and acl.tax_amount is not null
                            and amp."value" is null ) then
                                ( acl.price_subtotal + acl.tax_amount )
                            when ( acm.move_type <> 'out_refund'
                            and acl.tax_amount is null
                            and amp."value" is not null ) then
                                ( acl.price_subtotal - amp."value" )
                            when ( acm.move_type <> 'out_refund'
                            and acl.tax_amount is not null
                            and amp."value" is not null ) then
                                ( acl.price_subtotal - amp."value" - acl.tax_amount )
                            else 0
                        end as price_subtotal_incl,
                        case
                            when sol.x_free_good = true then
                                'unconditional'
                            when ( sol.x_free_good = false
                            and acl.price_subtotal = 0 ) then
                                'conditional'
                            else ''
                        end as gift,
                        acl.promotions,
                        p1.product_group,
                        p1.product_line,
                        p1.texture_name,
                        p1.detailed_type,
                        acm.move_type,
                        whs.whs_type,
                        whs.name as warehouse_type,
                        sod.source_record,
                        par.code,
                        acm.company_id as company_id,
                        p1.valuation_account
                    from
                        sale_order_line_invoice_rel sli
                    left join account_move_line acl on
                        acl."id" = sli.invoice_line_id
                    left join account_move_promotion amp on
                        ( amp.move_id = acl.move_id
                            and amp.product_id = acl.product_id )
                    left join account_move acm on
                        acm."id" = acl.move_id
                    left join (
                        select
                            cus."id" as partner_id,
                            rpg.code
                        from
                            res_partner cus
                        left join res_partner_group rpg on
                            rpg.id = cus.group_id
                                                                ) as par on
                        par.partner_id = acm.partner_id
                    left join account_move_line_account_tax_rel mtx on
                        mtx.account_move_line_id = acl."id"
                    left join account_tax atx on
                        atx."id" = mtx.account_tax_id
                    left join sale_order_line sol on
                        sol."id" = sli.order_line_id
                    left join sale_order sod on
                        sod."id" = sol.order_id
                    left join (
                        select
                            loc.ID as location_id,
                            stw."id" as warehouse_id,
                            stw."name" as warehouse_name,
                            CONCAT ( stw."name",
                            '/',
                            loc."name" ) as location_name,
                            stw.whs_type,
                            wht."name"
                        from
                            stock_location loc
                        left join stock_warehouse stw on
                            stw."id" = loc.warehouse_id
                        left join stock_warehouse_type wht on
                            wht."id" = stw.whs_type 
                        ) as whs on
                        whs.location_id = sol.x_location_id
                    left join (
                        select
                            prd."id" as product_id,
                            coalesce ( uom.NAME :: JSON ->> 'vi_VN',
                            uom.NAME :: JSON ->> 'en_US' ) :: text as uom_name,
                            prt.detailed_type,
                            prt.voucher,
                            coalesce ( prt.NAME :: JSON ->> 'vi_VN',
                            prt.NAME :: JSON ->> 'en_US' ) :: text as product_name,
                            split_part( ctg.complete_name,
                            ' / ',
                            2 ) as product_group,
                            split_part( ctg.complete_name,
                            ' / ',
                            3 ) as product_line,
                            split_part( ctg.complete_name,
                            ' / ',
                            4 ) as texture_name,
                            prt.barcode,
                            aa.code as valuation_account
                        from
                            product_product prd
                        left join product_template prt on
                            prt.ID = prd.product_tmpl_id
                        left join product_category ctg on
                            ctg."id" = prt.categ_id
                        left join uom_uom uom on
                            uom.ID = prt.uom_id 
                        left join ir_property ip on ip.res_id = 'product.category,' || prt.categ_id AND ip."name" = 'property_stock_valuation_account_id' and ip.company_id = {self.env.company.id}
                        left join account_account aa on 'account.account,' || aa.id = ip.value_reference
                        ) p1 on
                        p1.product_id = acl.product_id
                    where
                        acm."state" = 'posted'
                        and ( P1.detailed_type = 'product'
                            or ( P1.detailed_type = 'service'
                                and P1.voucher = true ) )
                        and acm.move_type like 'out%'
                        and acl.product_id is not null
                        and acm.journal_id = 18
                        and acl.tax_amount is null                                                                                                                 
                        ) as por
                left join attrs on attrs.product_id = por.product_id
                where
                    1=1
            """
        if self.date_from and self.date_to:
            query += f" and {format_date_query('por.date_order', tz_offset)} between '{self.date_from}' and '{self.date_to}'"
        if self.product_ids:
            query += f" and por.product_id = any(array{self.product_ids.ids})"
        if self.warehouse_ids:
            query += f" and por.warehouse_id = any(array{self.warehouse_ids.ids})"
        if self.group_id:
            query += f" and por.product_group = '{self.group_id.name}'"
        if self.line_id:
            query += f" and por.product_line = '{self.line_id.name}'"
        if self.structure_id:
            query += f" and por.texture_name = '{self.structure_id.name}'"
        if self.color:
            query += f" and attrs.color = '{self.color.name}'"
        if self.size:
            query += f" and attrs.size = '{self.size.name}'"
        if self.sale_channels == 'is_ecommerce':
            query += f" and por.is_nhanhvn is true"
        if self.sale_channels == 'is_inter_company':
            query += f" and por.code = '3000'"

        query += f"""
            group by
                por.barcode,
                por.product_name,
                por.warehouse_name,
                por.location_name,
                {'por.price_tax,' if self.is_get_price_unit else ''}
                por.tax_rate,
                por.product_group,
                por.product_line,
                por.texture_name,
                por.warehouse_type,
                por.gift,
                color,
                size,
                por.uom_name,
                por.valuation_account,
                por.warehouse_id
            order by
                por.gift ,
                por.warehouse_name,
                por.barcode
        """
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        if not self.sale_channels:
            raise ValidationError('Vui lòng chọn kênh bán')
        if not self.warehouse_ids:
            raise ValidationError('Vui lòng chọn kho')
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        titles = copy.copy(TITLES)
        if not self.is_get_price_unit:
            titles.remove('Đơn giá')
        values.update({
            'titles': titles,
            "data": data,
            'column_add': self.is_get_price_unit,
        })
        return values

    def generate_xlsx_report(self, workbook, allowed_company):
        data = self.get_data(allowed_company)
        formats = self.get_format_workbook(workbook)
        sheet = workbook.add_worksheet('Báo cáo tích - tiêu điểm theo cửa hàng')
        sheet.set_row(3, 25)
        sheet.set_row(6, 35)
        sheet.freeze_panes(7, 0)
        company = self.env['res.company'].search([('id', 'in', allowed_company)])
        cong_ty = ', '.join(company.filtered(lambda f: f.name).mapped('name'))
        dia_chi = ', '.join(company.filtered(lambda f: f.street).mapped('street'))
        sheet.write(0, 0, f'Công ty: {cong_ty}', formats.get('normal_format'))
        sheet.write(1, 0, f'Địa chỉ: {dia_chi}', formats.get('normal_format'))
        sheet.write(3, 0, 'Báo cáo doanh thu theo sản phẩm', formats.get('header_format'))
        sheet.write(4, 0, f"Báo cáo Từ ngày: {self.date_from.strftime('%d/%m/%Y %H:%M:%S')} Đến ngày: {self.date_to.strftime('%d/%m/%Y %H:%M:%S')}",
                    formats.get('italic_format'))
        for idx, title in enumerate(data.get('titles')):
            sheet.write(6, idx, title, formats.get('title_format'))
        sheet.set_column(1, len(data.get('titles')) - 1, 20)
        row = 7
        index = 0
        column_x = 10 if self.is_get_price_unit else 9
        data_list = data.get('data')
        products = list(filter(lambda x: x['gift'] == '', data_list))
        conditional = list(filter(lambda x: x['gift'] == 'conditional', data_list))
        unconditional = list(filter(lambda x: x['gift'] == 'unconditional', data_list))

        def write_excel(sheet, data, index, row):
            for value in data:
                index += 1
                sheet.write(row, 0, index, formats.get('center_format'))
                sheet.write(row, 1, value.get('warehouse_name') or '', formats.get('normal_format'))
                sheet.write(row, 2, value.get('location_name') or '', formats.get('normal_format'))
                sheet.write(row, 3, value.get('barcode') or '', formats.get('normal_format'))
                sheet.write(row, 4, value.get('product_name') or '', formats.get('normal_format'))
                sheet.write(row, 5, value.get('size') or '', formats.get('normal_format'))
                sheet.write(row, 6, value.get('color') or '', formats.get('normal_format'))
                sheet.write(row, 7, value.get('uom_name') or '', formats.get('normal_format'))
                sheet.write(row, 8, value.get('qty') or 0, formats.get('int_number_format'))
                if self.is_get_price_unit:
                    sheet.write(row, 9, value.get('price_tax') or 0, formats.get('int_number_format'))
                sheet.write(row, column_x, f"{value.get('tax_amount') or 0}%", formats.get('normal_format'))
                sheet.write(row, column_x + 1, value.get('revenues_511') or 0, formats.get('int_number_format'))
                sheet.write(row, column_x + 2, value.get('discount_amount') or 0, formats.get('int_number_format'))
                sheet.write(row, column_x + 3, value.get('revenue_deduction') or 0, formats.get('int_number_format'))
                sheet.write(row, column_x + 4, value.get('price_subtotal_incl') or 0, formats.get('int_number_format'))
                sheet.write(row, column_x + 5, value.get('product_group') or '', formats.get('normal_format'))
                sheet.write(row, column_x + 6, value.get('product_line') or '', formats.get('normal_format'))
                sheet.write(row, column_x + 7, value.get('texture_name') or '', formats.get('normal_format'))
                sheet.write(row, column_x + 8, value.get('valuation_account') or '', formats.get('normal_format'))
                sheet.write(row, column_x + 9, value.get('warehouse_type') or '', formats.get('normal_format'))
                row += 1
            return index, row

        index, row = write_excel(sheet=sheet, data=products, index=index, row=row)
        if conditional:
            sheet.merge_range(row, 0, row, len(data.get('titles')) - 1, 'Hàng tặng có điều kiện', formats.get('line_group_format'))
            row += 1
            index += 1
            index, row = write_excel(sheet=sheet, data=conditional, index=index, row=row)
        if unconditional:
            sheet.merge_range(row, 0, row, len(data.get('titles')) - 1, 'Hàng tặng không có điều kiện', formats.get('line_group_format'))
            row += 1
            index += 1
            index, row = write_excel(sheet=sheet, data=unconditional, index=index, row=row)

    def print_xlsx(self):
        if not self.warehouse_ids:
            raise ValidationError('Vui lòng chọn kho')
        return super().print_xlsx()

    @api.model
    def get_format_workbook(self, workbook):
        res = dict(super().get_format_workbook(workbook))
        line_group_format = {
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#98cfe1',
            'color': '#000000',
        }
        line_group_format = workbook.add_format(line_group_format)
        res.update({
            'line_group_format': line_group_format,
        })
        return res
