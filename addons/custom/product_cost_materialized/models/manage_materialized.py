# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, except_orm
from datetime import datetime


class ManageMaterialized(models.Model):
    _name = 'manage.materialized'
    _order = "to_date desc"
    _description = 'Manage Materialized'

    _sql_constraints = [('unique_name', 'unique(name)', 'Name must be unique')]

    name = fields.Char('Name', readonly=True)
    from_date = fields.Date('From date', required=True)
    to_date = fields.Date('To date', required=True)

    @api.model
    def create(self, values):
        result = super(ManageMaterialized, self).create(values)
        from_date = result.from_date.strftime('%d/%m/%Y')
        to_date = result.to_date.strftime('%d/%m/%Y')
        str_from_date = result.from_date.strftime('%d_%m_%Y')
        str_to_date = result.to_date.strftime('%d_%m_%Y')
        result.name = 'materialized_account_stock_' + str_from_date + '_' + str_to_date
        result._create_materialized(from_date, to_date)
        return result
    
    def _is_materialized_exists(self, name):
        cr = self._cr
        query = "SELECT matviewname FROM pg_matviews WHERE matviewname = %s"
        cr.execute(query, (name,))
        result = cr.dictfetchall()
        if result:
            return True
        return False

    def _create_materialized(self, str_from_date, str_to_date):
        self._drop_materialized()
        config_id = self.env['manage.materialized'].search([('to_date', '<', datetime.strptime(str_from_date, '%d/%m/%Y').date()),('id', '!=',  self.id)], order='to_date desc', limit=1)
        if config_id:
            materialized_config = config_id.name
            create_query = """
                CREATE MATERIALIZED VIEW public.""" + self.name + """ AS
                    (SELECT * FROM
                        (SELECT account_id, product_id, uom_id,
                                ROUND(SUM(tondk)) tondk, ROUND(SUM(gttondk)) gttondk, ROUND(SUM(nhap)) nhap, ROUND(SUM(gtnhap)) gtnhap, 
                                ROUND(SUM(xuat)) xuat, ROUND(SUM(gtxuat)) gtxuat, 
                                ROUND((SUM(tondk) + SUM(nhap) - SUM(xuat))) as tonck, ROUND((SUM(gttondk) + SUM(gtnhap) - SUM(gtxuat))) as gttonck
                        FROM (
                                -- tồn kho đầu kỳ
                                SELECT account_id, product_id, uom_id,
                                        tonck as tondk, gttonck as gttondk, 0 as nhap, 0 as gtnhap, 0 as xuat, 0 as gtxuat, 0 as tonck, 0 as gttonck
                                FROM """ + materialized_config + """

                                UNION ALL
                                -- xuất nhập trong kỳ
                                SELECT  aa.id account_id, c.id product_id, g.id uom_id,
                                        0 tondk, 0 gttondk,
                                        sum(case when a.x_type_transfer = 'in' then abs(a.quantity/coalesce(f.factor,1)) else 0 end) nhap,
                                        sum(case when a.x_type_transfer = 'in' then abs(a.debit) else 0 end) gtnhap, 				
                                        sum(case when a.x_type_transfer = 'out' then abs(a.quantity/coalesce(f.factor,1)) else 0 end) xuat,
                                        sum(case when a.x_type_transfer = 'out' then abs(a.credit) else 0 end) gtxuat, 0 tonck, 0 gttonck
                                FROM account_move_line a
                                JOIN account_move b ON b.id = a.move_id
                                JOIN account_account aa ON aa.id = a.account_id
                                JOIN product_product c ON c.id = a.product_id
                                LEFT JOIN product_template pt ON pt.id = c.product_tmpl_id
                                LEFT JOIN uom_uom f ON f.id = a.product_uom_id
                                LEFT JOIN uom_uom g ON g.id = pt.uom_id
                                WHERE b.state = 'posted'
                                AND a.date >= to_date('""" + str_from_date + """','dd/mm/yyyy')
                                AND a.date <= to_date('""" + str_to_date + """','dd/mm/yyyy')
                                AND a.account_id in (SELECT SPLIT_PART(value_reference, ',', 2)::INTEGER
                                                    FROM ir_property WHERE name = 'property_stock_valuation_account_id'
                                                    GROUP BY value_reference)
                                GROUP BY aa.id,c.id,g.id) as bang
                        GROUP BY account_id, product_id, uom_id
                        ORDER BY product_id) as bang_tong_hop
                    WHERE (tondk != 0 or gttondk != 0 or nhap != 0 or gtnhap != 0 or xuat != 0 or gtxuat != 0 or tonck != 0 or gttonck != 0))
                """
        else:
            create_query = """
            CREATE MATERIALIZED VIEW public.""" + self.name + """ AS
                (SELECT * FROM
                    (SELECT account_id, product_id, uom_id,
                                ROUND(SUM(tondk)) tondk, ROUND(SUM(gttondk)) gttondk, ROUND(SUM(nhap)) nhap, ROUND(SUM(gtnhap)) gtnhap, 
                                ROUND(SUM(xuat)) xuat, ROUND(SUM(gtxuat)) gtxuat, 
                                ROUND((SUM(tondk) + SUM(nhap) - SUM(xuat))) as tonck, ROUND((SUM(gttondk) + SUM(gtnhap) - SUM(gtxuat))) as gttonck
                    FROM (
                            SELECT  aa.id account_id, c.id product_id, g.id uom_id, 
                                    0 tondk, 0 gttondk,
                                    sum(case when a.x_type_transfer = 'in' then abs(a.quantity/coalesce(f.factor,1)) else 0 end) nhap,
                                    sum(case when a.x_type_transfer = 'in' then abs(a.debit) else 0 end) gtnhap, 				
                                    sum(case when a.x_type_transfer = 'out' then abs(a.quantity/coalesce(f.factor,1)) else 0 end) xuat,
                                    sum(case when a.x_type_transfer = 'out' then abs(a.credit) else 0 end) gtxuat, 0 tonck, 0 gttonck
                            FROM account_move_line a
                            LEFT JOIN account_move b ON b.id = a.move_id
                            LEFT JOIN account_account aa ON aa.id = a.account_id
                            LEFT JOIN product_product c ON c.id = a.product_id
                            LEFT JOIN product_template pt ON pt.id = c.product_tmpl_id
                            LEFT JOIN uom_uom f ON f.id = a.product_uom_id
                            LEFT JOIN uom_uom g ON g.id = pt.uom_id
                            WHERE b.state = 'posted'
                            AND a.date <= to_date('""" + str_to_date + """','dd/mm/yyyy')
                            AND a.account_id in (SELECT SPLIT_PART(value_reference, ',', 2)::INTEGER
                                                    FROM ir_property WHERE name = 'property_stock_valuation_account_id'
                                                    GROUP BY value_reference)
                            GROUP BY aa.id,c.id,g.id) as bang
                    GROUP BY account_id, product_id, uom_id
                    ORDER BY product_id) as bang_tong_hop
                WHERE (tondk != 0 or gttondk != 0 or nhap != 0 or gtnhap != 0 or xuat != 0 or gtxuat != 0 or tonck != 0 or gttonck != 0))
            """
        self._cr.execute(create_query)

    def _drop_materialized(self):
        if self._is_materialized_exists(self.name):
            drop_query = "DROP MATERIALIZED VIEW " + self.name + " CASCADE"
            self._cr.execute(drop_query,)
        return True

    def refresh_materialized(self):
        if self._is_materialized_exists(self.name):
            refresh_query = "REFRESH MATERIALIZED VIEW " + self.name
            self._cr.execute(refresh_query,)
        return True

    def write(self, values):
        result = super(ManageMaterialized, self).write(values)
        if 'from_date' in values or 'to_date' in values:
            from_date = self.from_date.strftime('%d/%m/%Y')
            to_date = self.to_date.strftime('%d/%m/%Y')
            str_from_date = self.from_date.strftime('%d_%m_%Y')
            str_to_date = self.to_date.strftime('%d_%m_%Y')
            self.name = 'materialized_account_stock_' + str_from_date + '_' + str_to_date
            self._create_materialized(from_date, to_date)
        return result

    def unlink(self):
        for order in self:
            order._drop_materialized()
        return super(ManageMaterialized, self).unlink()
    

    def action_cron_month_manage_materialized(self):
        pass