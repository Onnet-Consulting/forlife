DROP FUNCTION IF EXISTS stock_incoming_outgoing_report_account;
CREATE OR REPLACE FUNCTION stock_incoming_outgoing_report_account(_date_from character varying , _date_to character varying, _company_id integer)
RETURNS TABLE
        (
            product_id               INTEGER,
            opening_quantity         NUMERIC,
            opening_value            NUMERIC,
            incoming_quantity        NUMERIC,
            incoming_value           NUMERIC,
            odoo_outgoing_quantity   NUMERIC,
            real_outgoing_value      NUMERIC,
            closing_quantity         NUMERIC,
            closing_value            NUMERIC
        )
    LANGUAGE plpgsql
AS
$BODY$

BEGIN
    RETURN Query (
        WITH opening as (
            -- đầu kỳ
            select sm.product_id,
                    sum(case when spt.code = 'incoming' then coalesce(sm.quantity_done, 0)
                            when spt.code = 'outgoing' then coalesce(-sm.quantity_done, 0)
                                end) as quantity,
                    sum(aml.balance) as total_value
            from account_move_line aml
            left join account_move am on am.id = aml.move_id
            left join stock_move sm on sm.id = am.stock_move_id and am.stock_move_id is not null
            left join product_product pp on pp.id = sm.product_id
            left join product_template pt on pt.id = pp.product_tmpl_id
            left join stock_picking_type spt on spt.id = sm.picking_type_id
            where sm.state = 'done'
            and sm.date < _date_from::timestamp
            and sm.company_id = _company_id
            and spt.code in ('incoming', 'outgoing')
            and pt.detailed_type = 'product'
            and aml.account_id = (select split_part(value_reference, ',', 2)::integer
                                from ir_property
                                where name = 'property_stock_valuation_account_id'
                                and res_id = 'product.category,' || (select pt.categ_id from product_product pp
                                                                    join product_template pt on pp.product_tmpl_id = pt.id
                                                                    where pp.id = aml.product_id)
                                                                    and company_id = _company_id)
            group by sm.product_id
        ),
        incoming as (
            -- nhập trong kỳ
            select sm.product_id,
                    sum(sm.quantity_done) as quantity,
                    sum(aml.balance) as total_value
            from account_move_line aml
            left join account_move am on am.id = aml.move_id
            left join stock_move sm on sm.id = am.stock_move_id and am.stock_move_id is not null
            left join product_product pp on pp.id = sm.product_id
            left join product_template pt on pt.id = pp.product_tmpl_id
            left join stock_picking_type spt on spt.id = sm.picking_type_id
            where sm.state = 'done'
            and sm.date <= _date_from::timestamp and sm.date >= _date_to::timestamp
            and sm.company_id = _company_id
            and spt.code in ('incoming')
            and pt.detailed_type = 'product'
            and aml.account_id = (select split_part(value_reference, ',', 2)::integer
                                from ir_property
                                where name = 'property_stock_valuation_account_id'
                                and res_id = 'product.category,' || (select pt.categ_id from product_product pp
                                                                    join product_template pt on pp.product_tmpl_id = pt.id
                                                                    where pp.id = aml.product_id)
                                                                    and company_id = _company_id)
            group by sm.product_id
        ),
        outgoing as (
            -- xuất trong kỳ
            select sm.product_id,
                    sum(sm.quantity_done) as quantity,
                    sum(aml.balance) as total_value
            from account_move_line aml
            left join account_move am on am.id = aml.move_id
            left join stock_move sm on sm.id = am.stock_move_id and am.stock_move_id is not null
            left join product_product pp on pp.id = sm.product_id
            left join product_template pt on pt.id = pp.product_tmpl_id
            left join stock_picking_type spt on spt.id = sm.picking_type_id
            where sm.state = 'done'
            and sm.date <= _date_from::timestamp and sm.date >= _date_to::timestamp
            and sm.company_id = _company_id
            and spt.code in ('outgoing')
            and pt.detailed_type = 'product'
            and aml.account_id = (select split_part(value_reference, ',', 2)::integer
                                from ir_property
                                where name = 'property_stock_valuation_account_id'
                                and res_id = 'product.category,' || (select pt.categ_id from product_product pp
                                                                    join product_template pt on pp.product_tmpl_id = pt.id
                                                                    where pp.id = aml.product_id)
                                                                    and company_id = _company_id)
            group by sm.product_id
        )

        SELECT data.*,
                (case when data.opening_quantity + data.incoming_quantity = 0 then 0
                    else (data.opening_value + data.incoming_value) / (data.opening_quantity + data.incoming_quantity) * data.odoo_outgoing_quantity
                end) as real_outgoing_value,
                (data.opening_quantity + data.incoming_quantity - data.odoo_outgoing_quantity) as closing_quantity,
                (data.opening_value + data.incoming_value - (case when data.opening_quantity + data.incoming_quantity = 0 then 0
                                                                        else (data.opening_value + data.incoming_value) / (data.opening_quantity + data.incoming_quantity) * data.odoo_outgoing_quantity
                                                                        end)
                ) as closing_value
        FROM
            (SELECT pp.id as product_id,
                    coalesce(opening.quantity, 0) as opening_quantity,
                    coalesce(opening.total_value, 0) as opening_value,
                    coalesce(incoming.quantity, 0) as incoming_quantity,
                    coalesce(incoming.total_value, 0) as incoming_value,
                    coalesce(outgoing.quantity, 0) as odoo_outgoing_quantity
            FROM product_product pp
            LEFT JOIN opening ON opening.product_id = pp.id
            LEFT JOIN incoming ON incoming.product_id = pp.id
            LEFT JOIN outgoing ON outgoing.product_id = pp.id
            ORDER BY pp.default_code) as data
        WHERE data.opening_quantity <> 0
            OR data.incoming_quantity <> 0
            OR data.odoo_outgoing_quantity <> 0
    );
END;

$BODY$;
-- select * from stock_incoming_outgoing_report('2023-01-31 23:00:00', '2023-02-19 22:59:59', 1)
