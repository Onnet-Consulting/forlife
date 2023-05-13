DROP FUNCTION IF EXISTS stock_incoming_outgoing_report_account;
CREATE OR REPLACE FUNCTION stock_incoming_outgoing_report_account(_date_from character varying , _date_to character varying, _company_id integer)
RETURNS TABLE
        (
            product_id               INTEGER,
            account_id               INTEGER,
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
        WITH end_date as (
            select sqp.product_id, sqp.account_id, max(sqp.period_end_date) max_period_end_date
            from stock_quant_period sqp
            where sqp.period_end_date <= _date_from::date
            and sqp.company_id = _company_id
            group by sqp.product_id, sqp.account_id
        ), opening as (
            -- đầu kỳ
            SELECT dataa.product_id,
                    dataa.account_id,
                    sum(dataa.quantity) as quantity,
                    sum(dataa.total_value) as total_value
            FROM (
                SELECT sqp.product_id, sqp.account_id,
                    sqp.closing_quantity as quantity,
                    sqp.closing_value as total_value
                from stock_quant_period sqp
                where sqp.period_end_date = (select ed.max_period_end_date from end_date ed where ed.product_id = sqp.product_id and ed.account_id = sqp.account_id order by ed.max_period_end_date desc limit 1)

                union all

                select aml.product_id, aml.account_id,
                        aml.quantity as quantity,
                        aml.debit - aml.credit as total_value
                from account_move_line aml
                left join account_move am on am.id = aml.move_id
                left join product_product pp on pp.id = aml.product_id
                where 1=1
                and am.state = 'posted'
                and am.date < _date_from::date
                and (case when exists (select ed.max_period_end_date from end_date ed where ed.product_id = aml.product_id and ed.account_id = aml.account_id order by ed.max_period_end_date desc limit 1) then am.date > (select ed.max_period_end_date from end_date ed where ed.product_id = aml.product_id order by ed.max_period_end_date desc limit 1)
                    else 1 = 1 end)
                and am.company_id = _company_id
                and aml.account_id = (select split_part(value_reference, ',', 2)::integer
                                    from ir_property
                                    where name = 'property_stock_valuation_account_id'
                                    and res_id = 'product.category,' || (select pt.categ_id from product_product pp
                                                                        join product_template pt on pp.product_tmpl_id = pt.id
                                                                        where pp.id = aml.product_id)
                                                                        and company_id = _company_id)
            ) dataa
            group by dataa.product_id, dataa.account_id
        ),
        incoming as (
            -- nhập trong kỳ
            select aml.product_id, aml.account_id,
                    sum(aml.quantity) as quantity,
                    sum(aml.debit) as total_value
            from account_move_line aml
            left join account_move am on am.id = aml.move_id
            left join product_product pp on pp.id = aml.product_id
            where 1=1
            and aml.debit > 0
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
            group by aml.product_id, aml.account_id
        ),
        outgoing as (
            -- xuất trong kỳ
            select aml.product_id, aml.account_id,
                    sum(-aml.quantity) as quantity,
                    sum(aml.credit) as total_value
            from account_move_line aml
            left join account_move am on am.id = aml.move_id
            left join product_product pp on pp.id = aml.product_id
            where 1=1
            and aml.credit > 0
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
            group by aml.product_id, aml.account_id
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
                    coalesce(opening.account_id, coalesce(incoming.account_id, outgoing.account_id)) as account_id,
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
