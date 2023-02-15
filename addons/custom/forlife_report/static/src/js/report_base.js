odoo.define('forlife_report.report_base', function (require) {
    'use strict';

    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');

    let ReportBaseAction = AbstractAction.extend({
        init: function (parent, action) {
            this.actionManager = parent;
            this.odoo_context = action.context;
            this.report_model = this.odoo_context.report_model;
            return this._super.apply(this, arguments);
        },

        willStart: async function () {
            let self = this;
            const reportPromise = this._rpc({
                model: this.report_model,
                method: 'get_data',
                args: [this.report_options],
                context: this.odoo_context
            }).then(res => self.data = res)
            const parentPromise = this._super(...arguments);
            return Promise.all([reportPromise, parentPromise]);
        },
    });

    return ReportBaseAction;
})