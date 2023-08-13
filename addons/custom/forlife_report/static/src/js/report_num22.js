odoo.define('forlife_report.report_num22', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum22Action = ReportBaseAction.extend({
        events: _.extend({}, ReportBaseAction.prototype.events, {
            'click .show-detail': 'show_detail',
        }),

        parse_data: function (data) {
            this.title_layer2 = data.title_layer2;
            this._super(...arguments);
        },

        show_detail: function (e) {
            this.$('#transaction-detail').html(QWeb.render("ReportTransactionDetailTemplate", {
                "titles": this.title_layer2,
                "data": this.data[e.currentTarget.id].transaction_detail || [],
                "report_type_id": 'data_detail',
                "report_filename": 'Chi tiết giao dịch.xlsx',
                "format_decimal": this.func.format_decimal,
            }));
            let element_rm = document.getElementsByClassName("show-detail");
            if (element_rm.length > 0) {
                for (let line of element_rm) {
                    line.classList.remove("active_line")
                }
            }
            let element = document.getElementById(e.currentTarget.id);
            element.classList.add('active_line');
        },

    })

    core.action_registry.add('report_num22_action', ReportNum22Action)

    return ReportNum22Action;

})