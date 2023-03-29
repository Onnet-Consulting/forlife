odoo.define('forlife_report.report_num4', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum4Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum4Template',
    })

    core.action_registry.add('report_num4_action', ReportNum4Action)

    return ReportNum4Action;

})