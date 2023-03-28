odoo.define('forlife_report.report_num1', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum1Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum1Template',
    })

    core.action_registry.add('report_num1_action', ReportNum1Action)

    return ReportNum1Action;

})