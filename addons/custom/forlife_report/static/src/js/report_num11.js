odoo.define('forlife_report.report_num11', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum11Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum11Template',
        reportPager: false,
    })

    core.action_registry.add('report_num11_action', ReportNum11Action)

    return ReportNum11Action;

})