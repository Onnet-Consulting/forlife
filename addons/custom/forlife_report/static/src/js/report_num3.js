odoo.define('forlife_report.report_num3', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum3Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum3Template',
        reportTitle: _t("Stock in time range by warehouse"),
    })

    core.action_registry.add('report_num3_action', ReportNum3Action)

    return ReportNum3Action;

})