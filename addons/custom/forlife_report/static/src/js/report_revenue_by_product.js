odoo.define('forlife_report.revenue_by_product', function (require) {
    'use strict';

    const core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');


    let RevenueByProduct = ReportBaseAction.extend({
        reportTemplate: 'ReportRevenueByProduct',
    })

    core.action_registry.add('report_revenue_by_product', RevenueByProduct)

    return RevenueByProduct;

})