odoo.define('forlife_report.report_num8', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum8Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum8Template',
        reportPager: false,
    })

    core.action_registry.add('report_num8_action', ReportNum8Action)

    return ReportNum8Action;

})