odoo.define('forlife_report.report_base', function (require) {
    'use strict';

    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const QWeb = core.qweb;

    let ReportBaseAction = AbstractAction.extend({
        events: {
            'click button.o_pager_next': 'next_page',
            'click button.o_pager_previous': 'previous_page',
        },
        reportTemplate: 'ReportBase',

        init: function (parent, action) {
            this.actionManager = parent;
            this.odoo_context = action.context;
            this.report_model = this.odoo_context.report_model;
            this.RECORD_PER_PAGE = 80;
            return this._super.apply(this, arguments);
        },

        willStart: async function () {
            const reportPromise = this._rpc({
                model: this.report_model,
                method: 'get_data',
                args: [this.report_options],
                context: this.odoo_context
            }).then(res => this.parse_data(res))
            const parentPromise = this._super(...arguments);
            return Promise.all([reportPromise, parentPromise]);
        },

        start: async function () {
            await this._super(...arguments);
            this.render();
        },

        parse_data: function (data) {
            this.data = data;
            this.total_records = data.length;
            this.total_page = Math.floor(this.total_records / this.RECORD_PER_PAGE);
            this.options = {
                total_records: data.length,
                total_page: Math.floor(this.total_records / this.RECORD_PER_PAGE),
                page_num: 1,
                data: data
            }
        },

        next_page: function () {
            console.log('next bro')
            console.log(this.report_data)
        },

        previous_page: function () {
            console.log('previous dude')
            console.log(this.report_data)
        },

        render: function () {
            let self = this;
            this.$('.o_content').html(QWeb.render(this.reportTemplate, {
                "data": self.data,
                "options": self.options
            }))
        },
    });

    return ReportBaseAction;
})