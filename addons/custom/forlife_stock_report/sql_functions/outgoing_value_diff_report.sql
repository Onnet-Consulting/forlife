DROP FUNCTION IF EXISTS outgoing_value_diff_report;
CREATE OR REPLACE FUNCTION outgoing_value_diff_report(_date_from character varying , _date_to character varying, _company_id integer)
RETURNS TABLE
        (
            product_id               INTEGER,
            opening_quantity         NUMERIC,
            opening_value            NUMERIC,
            incoming_quantity        NUMERIC,
            incoming_value           NUMERIC,
            odoo_outgoing_quantity   NUMERIC,
            odoo_outgoing_value      NUMERIC,
            real_outgoing_price_unit NUMERIC,
            real_outgoing_value      NUMERIC
        )
    LANGUAGE plpgsql
AS
$BODY$

BEGIN
    RETURN Query (
        WITH opening as (
            -- đầu kỳ
            select sm.product_id,
                    sum(svl.quantity) as quantity,
                    sum(svl.value) as total_value
            from stock_valuation_layer svl
            left join stock_move sm on sm.id = svl.stock_move_id and svl.stock_move_id is not null
            left join product_product pp on pp.id = sm.product_id
            left join stock_picking_type spt on spt.id = sm.picking_type_id
            where sm.state = 'done'
            and sm.date < _date_from::timestamp
            and sm.company_id = _company_id
            and spt.code in ('incoming', 'outgoing')
            group by sm.product_id
        ),
        incoming as (
            -- nhập trong kỳ
            select sm.product_id,
                    sum(svl.quantity) as quantity,
                    sum(svl.value) as total_value
            from stock_valuation_layer svl
            left join stock_move sm on sm.id = svl.stock_move_id and svl.stock_move_id is not null
            left join product_product pp on pp.id = sm.product_id
            left join stock_picking_type spt on spt.id = sm.picking_type_id
            where sm.state = 'done'
            and sm.date >= _date_from::timestamp and sm.date <= _date_to::timestamp
            and sm.company_id = _company_id
            and spt.code in ('incoming')
            group by sm.product_id
        ),
        outgoing as (
            -- xuất trong kỳ
            select sm.product_id,
                    abs(sum(svl.quantity)) as quantity,
                    abs(sum(svl.value)) as total_value
            from stock_valuation_layer svl
            left join stock_move sm on sm.id = svl.stock_move_id and svl.stock_move_id is not null
            left join product_product pp on pp.id = sm.product_id
            left join stock_picking_type spt on spt.id = sm.picking_type_id
            where sm.state = 'done'
            and sm.date >= _date_from::timestamp and sm.date <= _date_to::timestamp
            and sm.company_id = _company_id
            and spt.code in ('outgoing')
            group by sm.product_id
        )

        SELECT data.*,
                (case when data.opening_quantity + data.incoming_quantity = 0 and data.incoming_quantity = 0 then 0
                      when data.opening_quantity + data.incoming_quantity = 0 and data.incoming_quantity <> 0 then data.incoming_value / data.incoming_quantity
                      else (data.opening_value + data.incoming_value) / (data.opening_quantity + data.incoming_quantity)
                end) as real_outgoing_price_unit,
                (case when data.opening_quantity + data.incoming_quantity = 0 then data.incoming_value
                      else (data.opening_value + data.incoming_value) / (data.opening_quantity + data.incoming_quantity) * data.odoo_outgoing_quantity
                end) as real_outgoing_value
        FROM
            (SELECT pp.id as product_id,
                    coalesce(opening.quantity, 0) as opening_quantity,
                    coalesce(opening.total_value, 0) as opening_value,
                    coalesce(incoming.quantity, 0) as incoming_quantity,
                    coalesce(incoming.total_value, 0) as incoming_value,
                    coalesce(outgoing.quantity, 0) as odoo_outgoing_quantity,
                    coalesce(outgoing.total_value, 0) as odoo_outgoing_value
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
-- select * from outgoing_value_diff_report('2023-01-31 23:00:00', '2023-02-19 22:59:59', 1)
