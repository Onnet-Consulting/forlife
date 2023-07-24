odoo.define('forlife_report.report_num5', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum5Action = ReportBaseAction.extend({
        events: _.extend({}, ReportBaseAction.prototype.events, {
            'click .show-employee-detail': 'show_employee_detail',
            'click .show-order-detail': 'show_order_detail',
        }),

        parse_data: function (data) {
            this.employee_detail = data.employee_detail;
            this.order_detail = data.order_detail;
            this.report_type_id = 'all_employee';
            this._super(...arguments);
        },

        show_employee_detail: function (e) {
            this.employee_id = e.currentTarget.id;
            let invoice_data = this.employee_detail.value_invoice_by_employee_id[this.employee_id];
            this.$('#employee-detail').html(QWeb.render("ReportEmployeeDetailTemplate", {
                "titles": this.employee_detail.title,
                "data_detail": invoice_data,
                "report_type_id": 'order_detail',
                "report_filename": 'Danh sách hóa đơn.xls',
                "format_decimal": this.func.format_decimal,
            }));
            this.$('#order-detail').html(QWeb.render("ReportOrderDetailTemplate", {
                "titles": false,
            }));
            this.invoice_key = false;
            let element_rm = document.getElementsByClassName("show-employee-detail");
            if (element_rm.length > 0){
                for (let line of element_rm){
                    line.classList.remove("active_line")
                }
            }
            let element = document.getElementById(this.employee_id);
            element.classList.add('active_line');
        },

        show_order_detail: function (e) {
            this.invoice_key = e.currentTarget.id;
            let order_data = this.order_detail.detail_invoice_by_order_key[this.invoice_key];
            this.$('#order-detail').html(QWeb.render("ReportOrderDetailTemplate", {
                "titles": this.order_detail.title,
                "data_detail": order_data,
                "report_type_id": 'employee_detail',
                "report_filename": 'Chi tiết giao dịch.xls',
                "format_decimal": this.func.format_decimal,
            }));
            let element_rm = document.getElementsByClassName("show-order-detail");
            if (element_rm.length > 0) {
                for (let line of element_rm){
                    line.classList.remove("active_line")
                }
            }
            let element = document.getElementById(this.invoice_key);
            element.classList.add('active_line');
        },

    })

    core.action_registry.add('report_num5_action', ReportNum5Action)

    return ReportNum5Action;

})