odoo.define('forlife_report.stock_price_by_warehouse', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let StockPriceByWarehouse = ReportBaseAction.extend({
        reportTemplate: 'ReportStockPriceByWarehouse',

        parse_data: function (data) {
            this.data = data.product_data;
            this.data_by_warehouse = data.data_by_warehouse_id;
            this.total_records = this.data.length;
            this.total_page = Math.ceil(this.total_records / this.record_per_page);
            this.options = this.build_options(1);
        },
    })

    core.action_registry.add('report_stock_sale_price', StockPriceByWarehouse)

    return StockPriceByWarehouse;

})