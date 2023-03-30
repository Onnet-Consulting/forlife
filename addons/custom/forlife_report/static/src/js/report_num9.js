odoo.define('forlife_report.report_num9', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum9Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum9Template',
        reportPager: false,
    })

    core.action_registry.add('report_num9_action', ReportNum9Action)

    return ReportNum9Action;

})