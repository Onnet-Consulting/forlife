DROP FUNCTION IF EXISTS outgoing_value_diff_account_report_picking_type;
CREATE OR REPLACE FUNCTION outgoing_value_diff_account_report_picking_type(_date_from character varying , _date_to character varying, _company_id integer)
RETURNS TABLE
        (
            product_id               INTEGER,
            picking_type_id          INTEGER,
            total_diff               NUMERIC,
            qty_percent              NUMERIC,
            value_diff               NUMERIC
        )
    LANGUAGE plpgsql
AS
$BODY$

BEGIN
    RETURN Query (
        WITH outgoing as (
            select sm.product_id, sm.picking_type_id, sum(-aml.quantity) as quantity
            from account_move_line aml
            left join account_move am on am.id = aml.move_id
            left join product_product pp on pp.id = aml.product_id
            left join stock_move sm on sm.id = am.stock_move_id
            left join stock_picking_type spt on spt.id = sm.picking_type_id
            where aml.credit > 0
            and am.state = 'posted'
            and am.date >= _date_from::date and am.date <= _date_to::date
            and am.company_id = _company_id
            and aml.account_id = (select split_part(value_reference, ',', 2)::integer
                                from ir_property
                                where name = 'property_stock_valuation_account_id'
                                and res_id = 'product.category,' || (select pt.categ_id from product_product pp
                                                                    join product_template pt on pp.product_tmpl_id = pt.id
                                                                    where pp.id = aml.product_id)
                                                                    and company_id = _company_id)
            group by sm.product_id, sm.picking_type_id
            order by sm.product_id, sm.picking_type_id
            )


        SELECT o.product_id,
            o.picking_type_id,
            data.total_diff,
            (coalesce(o.quantity, 0) / data.odoo_outgoing_quantity) * 100 as qty_percent,
            (coalesce(o.quantity, 0) / data.odoo_outgoing_quantity) * data.total_diff as value_diff
        FROM outgoing o
        LEFT JOIN
            (SELECT ovd.product_id, ovd.odoo_outgoing_quantity,
                (case when ovd.real_outgoing_value != 0 then (ovd.odoo_outgoing_value - ovd.real_outgoing_value) else 0 end) as total_diff
            FROM outgoing_value_diff_account_report(_date_from, _date_to, _company_id) ovd
            ) as data on data.product_id = o.product_id
        where data.total_diff != 0
    );
END;

$BODY$;
