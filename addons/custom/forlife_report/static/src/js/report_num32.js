odoo.define('forlife_report.report_num32', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');
    const QWeb = core.qweb;


    let ReportNum32Action = ReportBaseAction.extend({

        events: _.extend({}, ReportBaseAction.prototype.events, {
            'click .show-history-point-detail': 'show_history_detail',
        }),

        init: function (parent, action) {
            this.history_detail = [];
            return this._super.apply(this, arguments);
        },

        show_history_detail: function (e) {
            console.log(e)
            console.log(e.currentTarget.id)
            const self = this
            this._rpc({
                model: this.report_model,
                method: 'get_history_detail',
                args: [e.currentTarget.id]
            }).then(function (res) {
                console.log(res)
                self.$('#history-detail').html(QWeb.render("ReportHistoryDetail", {
                    "data": res || [],
                    "format_decimal": self.func.format_decimal,
                }));
            })


            let element_rm = document.getElementsByClassName("show-history-point-detail");
            if (element_rm.length > 0) {
                for (let line of element_rm) {
                    line.classList.remove("active_line")
                }
            }
            let element = document.getElementById(e.currentTarget.id);
            element.classList.add('active_line');
        },

    })

    core.action_registry.add('report_num32_action', ReportNum32Action)

    return ReportNum32Action;

})