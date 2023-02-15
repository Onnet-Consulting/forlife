odoo.define('forlife_report.revenue_by_product', function (require) {
    'use strict';

    let core = require('web.core');
    const ReportBaseAction = require('forlife_report.report_base');

    let RevenueByProduct = ReportBaseAction.extend({
        contentTemplate: 'ReportRevenueByProduct',
        contentMainTemplate: 'ReportRevenueByProductMain',

        start: async function() {
            await this._super(...arguments);
            let x = 1;
        }
    })

    core.action_registry.add('report_revenue_by_product', RevenueByProduct)

    return RevenueByProduct;

})