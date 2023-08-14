odoo.define('forlife_report.report_num12', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum12Action = ReportBaseAction.extend({
        events: _.extend({}, ReportBaseAction.prototype.events, {
            'click .show-detail': 'show_detail',
        }),

        parse_data: function (data) {
            this.title_layer2 = data.title_layer2;
            this._super(...arguments);
        },

        show_detail: function (e) {
            this.key_data = e.currentTarget.id;
            let data = this.data[this.key_data].value_detail;
            this.$('#value-detail').html(QWeb.render("ReportValueDetailTemplate", {
                "titles": this.title_layer2,
                "data": data,
                "report_type_id": 'data_detail',
                "report_filename": 'Chi tiết.xlsx',
                "format_decimal": this.func.format_decimal,
            }));
            let element_rm = document.getElementsByClassName("show-detail");
            if (element_rm.length > 0) {
                for (let line of element_rm) {
                    line.classList.remove("active_line")
                }
            }
            let element = document.getElementById(this.key_data);
            element.classList.add('active_line');
        },

    })

    core.action_registry.add('report_num12_action', ReportNum12Action)

    return ReportNum12Action;

})