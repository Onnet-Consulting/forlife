odoo.define('forlife_report.report_num10', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let ReportNum10Action = ReportBaseAction.extend({
        reportTemplate: 'ReportNum10Template',
        reportPager: false,
    })

    core.action_registry.add('report_num10_action', ReportNum10Action)

    return ReportNum10Action;

})