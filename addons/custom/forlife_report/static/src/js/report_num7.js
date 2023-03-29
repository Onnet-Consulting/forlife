odoo.define('forlife_report.report_num7', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum7Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum7Template',
        reportPager: false,
    })

    core.action_registry.add('report_num7_action', ReportNum7Action)

    return ReportNum7Action;

})