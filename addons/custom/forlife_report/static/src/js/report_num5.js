odoo.define('forlife_report.report_num5', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum5Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum5Template',
        reportTitle: _t("Report revenue by employee"),
        reportPager: false,

        events: {
            'click .show-employee-detail': 'show_employee_detail',
            'click .show-order-detail': 'show_order_detail',
            'click .export_all': 'action_export_all',
            'click .export_employee_detail': 'action_export_employee_detail',
            'click .export_order_detail': 'action_export_order_detail',
        },

        parse_data: function (data) {
            this.employee_detail = data.employee_detail;
            this.order_detail = data.order_detail;
            this.column_add = data.column_add;
            this._super(...arguments);
        },

        show_employee_detail: function (e) {
            this.employee_id = e.currentTarget.id;
            let invoice_data = this.employee_detail.value_invoice_by_employee_id[this.employee_id];
            this.$('#employee-detail').html(QWeb.render("ReportEmployeeDetailTemplate", {
                "titles": this.employee_detail.title,
                "data_detail": invoice_data
            }))
            this.$('#order-detail').html(QWeb.render("ReportOrderDetailTemplate", {
                "titles": false,
            }))
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
                "data_detail": order_data
            }))
            let element_rm = document.getElementsByClassName("show-order-detail");
            if (element_rm.length > 0) {
                for (let line of element_rm){
                    line.classList.remove("active_line")
                }
            }
            let element = document.getElementById(this.invoice_key);
            element.classList.add('active_line');
        },

        action_export_all: function (e){
            this.export_data_by_id('all_employee', 'Doanh thu theo nhân viên.xlsx');
        },

        action_export_employee_detail: function (e){
            this.export_data_by_id('employee_detail', 'Danh sách hóa đơn.xlsx');
        },

        action_export_order_detail: function (e){
            this.export_data_by_id('order_detail', 'Chi tiết giao dịch.xlsx');
        },

        export_data_by_id: function (id, filename){
            var downloadLink;
            var dataType = 'application/vnd.ms-excel; charset=utf-8;';
            var tableSelect = document.getElementById(id);
            var tableHTML = tableSelect.outerHTML.replace(/ /g, '%20');
            downloadLink = document.createElement("a");
            document.body.appendChild(downloadLink);
            if(navigator.msSaveOrOpenBlob){
                var blob = new Blob(['\ufeff', tableHTML], {
                    type: dataType
                });
                navigator.msSaveOrOpenBlob( blob, filename);
            }else{
                downloadLink.href = 'data:' + dataType + ', ' + tableHTML;
                downloadLink.download = filename;
                downloadLink.click();
            }
        },
    })

    core.action_registry.add('report_num5_action', ReportNum5Action)

    return ReportNum5Action;

})