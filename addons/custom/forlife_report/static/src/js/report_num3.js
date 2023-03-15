odoo.define('forlife_report.report_num3', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum3Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum3Template',
        reportTitle: _t("Stock in time range by warehouse"),

        parse_data: function (data) {
            this.warehouse_name_by_id = data.warehouse_name_by_id;
            this.warehouse_names = data.warehouse_names;
            this.warehouse_ids = data.warehouse_ids;
            this._super(...arguments);
        },

        // build_options: function (page_num) {
        //     let options = this._super(...arguments);
        //     options.warehouse_data = this.warehouse_data;
        // },
    })

    core.action_registry.add('report_num3_action', ReportNum3Action)

    return ReportNum3Action;

})