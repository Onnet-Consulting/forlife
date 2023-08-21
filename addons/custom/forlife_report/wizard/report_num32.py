# -*- coding:utf-8 -*-

from odoo import api, fields, models, _

TITLES = [
    'Mã khách hàng', 'Ngày sinh', 'Nghề nghiệp', 'Email', 'CMND',
    'Địa chỉ', 'Tổng tích lũy', 'Tổng tiêu TL', 'Tổng trả TL',
    'Tích lũy hiện có', 'Ngày tích lũy gần nhất', 'Tiền tích lũy gần nhất'
]


class ReportNum28(models.TransientModel):
    _name = 'report.num32'
    _inherit = 'report.base'
    _description = 'Tra cứu thông tin điểm tích lũy'

    brand = fields.Selection([('tokyolife', 'TokyoLife'), ('format', 'Format')], string='Thương hiệu', required=True)
    phone = fields.Char(string='Số điện thoại', required=True)

    def _get_query(self):
        self.ensure_one()
        query = f"""
                with last_history as (
                    select
                        php.id,
                        php.partner_id,
                        date_order,
                        points_coefficient + points_fl_order as last_point
                    from
                        partner_history_point php
                    join res_partner rp on
                        php.partner_id = rp.id
                    where
                        rp.phone = '{self.phone}'
                        and php.store = '{'forlife' if self.brand == 'tokyolife' else 'format'}'
                    order by
                        php.id desc
                    limit 1),
                    payment as (
                    select
                        po.id,
                        sum(ppm.amount) as amount
                    from
                        partner_history_point php
                    join pos_order po on
                        po.id = php.pos_order_id
                    join res_partner rp on
                        rp.id = po.partner_id
                    join pos_payment ppm on
                        po.id = ppm.pos_order_id
                    where 
                        rp.phone = '{self.phone}'
                        and php.store = '{'forlife' if self.brand == 'tokyolife' else 'format'}'
                    group by
                        po.id
                    ),
                    history as (
                    select
                        rp.id,
                        rp.ref as ma_kh,
                        rp.name as ho_ten,
                        rp.email as email,
                        rp.phone as dien_thoai,
                        '' as cccd,
                        rp.birthday as ngay_sinh,
                        hj.name as nghe_nghiep,
                        CONCAT_WS(', ',
                        rp.street,
                        rp.street2,
                        rp.city,
                        rcs.name,
                        coalesce (rc.name->>'vi_VN',
                        rc.name->>'en_US')) as dia_chi,
                        php.total_point as tong_tich_luy,
                        php.points_used as tong_tieu,
                        php.points_back as tong_tra,
                        php.points_store as hien_co,
                        php_detail.detail
                    from
                        res_partner rp
                    left join (
                        select
                            store,
                            partner_id,
                            sum(points_coefficient) + sum(points_fl_order) as total_point,
                            sum(points_used) as points_used,
                            sum(points_back) as points_back,
                            sum(points_coefficient) + sum(points_fl_order) - sum(points_used) - sum(points_back) as points_store
                        from
                            partner_history_point php1
                        group by
                            store,
                            partner_id
                    ) php on
                        php.partner_id = rp.id
                    left join hr_job hj on
                        hj.id = rp.job_id
                    left join res_country_state rcs on
                        rp.state_id = rcs.id
                    left join res_country rc on
                        rc.id = rp.country_id
                    left join (
                        select
                            php.partner_id as partner_id,
                            json_agg(to_json(php.*)) as detail
                        from
                            (
                            select
                                st.name as store,
                                po.name as ct,
                                TO_CHAR(
                                    php.date_order,
                                    'dd/mm/yyyy hh:mm:ss'
                                ) as date_order,
                                php.id,
                                php.partner_id,
                                sum(pol.qty) as qty,
                                po.amount_total,
                                sum(poldd.money_reduced) as money_reduced,
                                case
                                    when php.point_order_type = 'new' then 'Đơn mới'
                                    when php.point_order_type = 'back_order' then 'Đơn trả'
                                    when php.point_order_type = 'reset_order' then 'Reset điểm'
                                    when php.point_order_type = 'point compensate' then 'Tích điểm bù'
                                    when php.point_order_type = 'coefficient' then 'Hệ số'
                                    else ''
                                end as point_order_type,
                                php.points_fl_order as points_fl_order,
                                php.points_coefficient,
                                php.points_used,
                                php.points_back,
                                php.points_store,
                                p.amount as amount
                            from
                                partner_history_point php
                            left join res_partner rp on
                                rp.id = php.partner_id
                            left join pos_order po on
                                po.id = php.pos_order_id
                            left join pos_session ps on
                                po.session_id = ps.id
                            left join pos_config pc on
                                ps.config_id = pc.id
                            left join store st on
                                pc.store_id = st.id
                            left join pos_order_line pol on
                                po.id = pol.order_id
                            left join pos_order_line_discount_details poldd on
                                pol.id = poldd.pos_order_line_id
                            left join payment p on
                                p.id = po.id
                            where
                                php.store = '{'forlife' if self.brand == 'tokyolife' else 'format'}'
                                and rp.phone = '{self.phone}' and (pol.is_promotion is false or pol.is_promotion is null)
                            group by
                                st.name,
                                po.name,
                                php.date_order,
                                php.id,
                                php.partner_id,
                                po.amount_total,
                                point_order_type,
                                php.points_coefficient,
                                php.points_used,
                                php.points_back,
                                php.points_store,
                                points_fl_order,
                                amount
                    ) php
                        group by
                            php.partner_id
                    ) php_detail on
                        php_detail.partner_id = rp.id
                    where
                        rp.phone = '{self.phone}'
                        and php.store = '{'forlife' if self.brand == 'tokyolife' else 'format'}'
                    )
                    select
                        h.*,
                        TO_CHAR(
                            lh.date_order,
                            'dd/mm/yyyy hh:mm:ss'
                        ) as date_order,
                        lh.last_point
                    from
                        history h,
                        last_history lh
        """
        return query

    def get_data(self, allowed_company):
        self.ensure_one()
        values = dict(super().get_data(allowed_company))
        query = self._get_query()
        data = self.env['res.utility'].execute_postgresql(query=query, param=[], build_dict=True)
        values.update({
            'titles': TITLES,
            "data": data,
        })
        return values

    @api.model
    def get_history_detail(self, history_id):
        data = []
        history = self.env['partner.history.point'].browse(int(history_id))
        if history.pos_order_id:
            sql = f"""
                with dpos_order as (select
                    pp.barcode  as barcode,
                    coalesce (pt.name->>'vi_VN', pt.name->>'en_US') as name,
                    coalesce (uu.name->>'vi_VN', uu.name->>'en_US') as uom_name,
                    pol.qty as qty,
                    case when pt.is_voucher_auto then pol.price_unit else pol.original_price end as price,
                    pold.money_reduced as money_reduced
                    
                from pos_order po 
                join pos_order_line pol on po.id = pol.order_id 
                join product_product pp on pol.product_id = pp.id
                join product_template pt on pp.product_tmpl_id = pt.id
                join uom_uom uu on pt.uom_id = uu.id
                left join (
                    select pos_order_line_id, sum(money_reduced) as money_reduced from pos_order_line_discount_details group by pos_order_line_id
                ) pold on pol.id = pold.pos_order_line_id
                where po.id = {history.pos_order_id.id} and (pol.is_promotion is false or pol.is_promotion is null)
                )
                
                select 
                round((ddo.money_reduced/ddo.price) * 100, 0) as rate,
                (ddo.price * ddo.qty) - ddo.money_reduced as amount_total,
                ddo.* 
                from dpos_order ddo;
            """
            data = self.env['res.utility'].execute_postgresql(query=sql, param=[], build_dict=True)
        return data