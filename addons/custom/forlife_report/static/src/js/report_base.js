odoo.define('forlife_report.report_base', function (require) {
    'use strict';

    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const QWeb = core.qweb;

    let ReportBaseAction = AbstractAction.extend({
        init: function (parent, action) {
            this.actionManager = parent;
            this.odoo_context = action.context;
            this.report_model = this.odoo_context.report_model;
            return this._super.apply(this, arguments);
        },

        start: async function () {
            await this._super(...arguments);
            this.render();
        },

        willStart: async function () {
            const reportPromise = this._rpc({
                model: this.report_model,
                method: 'get_data',
                args: [this.report_options],
                context: this.odoo_context
            }).then(res => this.data = res)
            const parentPromise = this._super(...arguments);
            return Promise.all([reportPromise, parentPromise]);
        },

        render: function () {
            let self = this;
            self.update_cp();
            this.$('table.content').append(QWeb.render(this.contentMainTemplate, {"data": self.data}))
        },
    });

    return ReportBaseAction;
})