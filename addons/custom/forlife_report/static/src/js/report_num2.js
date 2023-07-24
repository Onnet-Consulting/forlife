odoo.define('forlife_report.report_num2', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum2Action = ReportBaseAction.extend({
        events: _.extend({}, ReportBaseAction.prototype.events, {
            'click .line_stock_detail': 'show_detail',
        }),

        parse_data: function (data) {
            this.detail_data_by_product_id = data.detail_data_by_product_id;
            this._super(...arguments);
        },

        show_detail: function (e) {
            let product_id = e.currentTarget.id;
            let product_data = this.detail_data_by_product_id[product_id];
            let product_name = e.currentTarget.querySelector('.product_name').textContent;
            this.$('#product-detail').html(QWeb.render("ReportNum2DetailTemplate", {
                "detail": {
                    product_name,
                    "lines": product_data
                },
                "format_decimal": this.func.format_decimal,
            }));
            let element_rm = document.getElementsByClassName("line_stock_detail");
            if (element_rm.length > 0){
                for (let line of element_rm){
                    line.classList.remove("active_line")
                }
            }
            let element = document.getElementById(product_id);
            element.classList.add('active_line');
        },
    })

    core.action_registry.add('report_num2_action', ReportNum2Action)

    return ReportNum2Action;

})