odoo.define('forlife_report.stock_price_by_warehouse', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum2Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum2Template',
        reportTitle: _t("Stock with sale price"),

        events: {
            'click .line_stock_detail': 'show_detail',
        },

        parse_data: function (data) {
            this.data = data.product_data;
            this.detail_data_by_product_id = data.detail_data_by_product_id;
            this.total_records = this.data.length;
            this.total_page = Math.ceil(this.total_records / this.record_per_page);
            this.options = this.build_options(1);
        },

        show_detail: function (e) {
            let product_id = e.currentTarget.id;
            let product_data = this.detail_data_by_product_id[product_id];
            let product_name = e.currentTarget.querySelector('.product_name').textContent;
            this.$('#product-detail').html(QWeb.render("ReportNum2DetailTemplate", {
                "detail": {
                    product_name,
                    "lines": product_data
                }
            }))
        },
    })

    core.action_registry.add('report_num2_action', ReportNum2Action)

    return ReportNum2Action;

})