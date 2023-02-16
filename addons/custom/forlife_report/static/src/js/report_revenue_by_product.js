odoo.define('forlife_report.revenue_by_product', function (require) {
    'use strict';

    const core = require('web.core');
    const _t = core._t;
    const ReportBaseAction = require('forlife_report.report_base');

    let RevenueByProduct = ReportBaseAction.extend({
        contentTemplate: 'ReportRevenueByProduct',
        contentMainTemplate: 'ReportRevenueByProductMain',

        update_cp: function () {
            let status = {
                title: _t('Revenue by product'),
            };
            return this.updateControlPanel(status);
        },

    })

    core.action_registry.add('report_revenue_by_product', RevenueByProduct)

    return RevenueByProduct;

})