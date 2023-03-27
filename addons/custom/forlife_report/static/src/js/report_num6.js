odoo.define('forlife_report.report_num6', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum6Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum6Template',
        reportTitle: _t("Report sale and stock"),
        reportPager: false,

        parse_data: function (data) {
            this.report_type_id = 'all_data';
            this.report_filename = 'Bán - trưng hàng.xlsx';
            this._super(...arguments);
        },
    })

    core.action_registry.add('report_num6_action', ReportNum6Action)

    return ReportNum6Action;

})