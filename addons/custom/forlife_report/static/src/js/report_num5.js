odoo.define('forlife_report.report_num5', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum5Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum5Template',
        reportTitle: _t("Report revenue by employee"),

        events: _.extend({}, ReportBaseAction.prototype.events, {
            'click .show-employee-detail': 'show_employee_detail',
            'click .show-order-detail': 'show_order_detail',
        }),

        parse_data: function (data) {
            this.employee_detail = data.employee_detail;
            this.order_detail = data.order_detail;
            this.column_add = data.column_add;
            this._super(...arguments);
        },

        show_employee_detail: function (e) {
            let employee_id = e.currentTarget.id;
            let invoice_data = this.employee_detail.value_invoice_by_employee_id[employee_id];
            this.$('#employee-detail').html(QWeb.render("ReportEmployeeDetailTemplate", {
                "titles": this.employee_detail.title,
                "data_detail": invoice_data
            }))
            this.$('#order-detail').html(QWeb.render("ReportOrderDetailTemplate", {
                "titles": false,
            }))
        },

        show_order_detail: function (e) {
            let invoice_key = e.currentTarget.id;
            let order_data = this.order_detail.detail_invoice_by_order_key[invoice_key];
            this.$('#order-detail').html(QWeb.render("ReportOrderDetailTemplate", {
                "titles": this.order_detail.title,
                "data_detail": order_data
            }))
        },
    })

    core.action_registry.add('report_num5_action', ReportNum5Action)

    return ReportNum5Action;

})