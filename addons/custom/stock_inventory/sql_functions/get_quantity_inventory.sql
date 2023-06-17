drop function if exists get_quantity_inventory;
create or replace function get_quantity_inventory(
                                                  _date_stop varchar,
                                                  _kho int[],
                                                  _mat_hang int[]
)
    returns table
            (
                product_id               integer,
                location_id              integer ,
                quanty                   numeric
            )
    LANGUAGE plpgsql
AS
$function$
begin
    return Query (

        with A as (
        select data_import.product_id, data_import.location_id,COALESCE(data_import.quanty,0) - COALESCE(data_export.quanty,0) as quanty from
            (select sm.product_id , sl.id as location_id, sum(sm.quantity_done) quanty from stock_move sm
                left join product_product pp on pp.id = sm.product_id
                left join stock_location sl on sl.id = sm.location_dest_id
                left join stock_picking sp on sp.id = sm.picking_id
                where pp.active is True
                and sp.date_done <= _date_stop::timestamp
                and sl.id in (select unnest(_kho))
                and (case when _mat_hang != array[]::integer[] then (pp.id IN (select unnest(_mat_hang))) else 1 = 1 end)
                group by sm.product_id , sl.id) as data_import
            left join
            (select sm.product_id , sl.id as location_id, sum(sm.quantity_done) quanty  from stock_move sm
                left join product_product pp on pp.id = sm.product_id
                left join stock_location sl on sl.id = sm.location_id
                left join stock_picking sp on sp.id = sm.picking_id
                where pp.active is True
                and sp.date_done <= _date_stop::timestamp
                and sl.id in (select unnest(_kho))
                and (case when _mat_hang != array[]::integer[] then (pp.id IN (select unnest(_mat_hang))) else 1 = 1 end)
                group by sm.product_id , sl.id)	as data_export
            on data_export.location_id = data_import.location_id and data_export.product_id = data_import.product_id
        )
        select * from A where A.quanty > 0

    );
end
$function$
;