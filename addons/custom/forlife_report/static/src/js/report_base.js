odoo.define('forlife_report.report_base', function (require) {
    'use strict';

    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const QWeb = core.qweb;
    const _t = core._t;

    let ReportBaseAction = AbstractAction.extend({
        events: {
            'click button.o_pager_next': 'next_page',
            'click button.o_pager_previous': 'previous_page',
        },
        reportTemplate: 'ReportBase',
        reportTitle: _t("Revenue by product"),
        record_per_page: 80,
        readDataTimeout: 300,

        init: function (parent, action) {
            this.actionManager = parent;
            this.odoo_context = action.context;
            this.report_model = this.odoo_context.report_model || this.odoo_context.active_model;
            this.report_id = this.odoo_context.active_id
            return this._super.apply(this, arguments);
        },

        willStart: async function () {
            const reportPromise = this._rpc({
                model: this.report_model,
                method: 'get_data',
                args: [this.report_id],
                context: this.odoo_context
            }, {
                // default timeout is 3 seconds
                // but some report need to handle large data,
                // so wait 'readDataTimeout' seconds  before concluding Odoo is unreachable.
                timeout: this.readDataTimeout,
            }).then(res => this.parse_data(res))
            const parentPromise = this._super(...arguments);
            return Promise.all([reportPromise, parentPromise]);
        },

        start: async function () {
            await this._super(...arguments);
            this.render();
        },

        build_options: function (page_num) {
            let start_record = (page_num - 1) * this.record_per_page + 1;
            let end_record = Math.min(page_num * this.record_per_page, this.total_records);
            let start_index = start_record - 1;
            return {
                page_num,
                start_record,
                end_record,
                total_records: this.total_records,
                data: this.data.slice(start_index, start_index + this.record_per_page)
            }
        },

        parse_data: function (data) {
            this.data = data;
            this.total_records = data.length;
            this.total_page = Math.ceil(this.total_records / this.record_per_page);
            this.options = this.build_options(1);
        },

        next_page: function () {
            let current_page = this.$('.o_current_page_num').text();
            let next_page = parseInt(current_page) + 1;
            if (next_page > this.total_page) next_page = 1;
            this.options = this.build_options(next_page);
            this.render();
        },

        previous_page: function () {
            let current_page = this.$('.o_current_page_num').text();
            let previous_page = parseInt(current_page) - 1;
            if (previous_page <= 0) previous_page = this.total_page;
            this.options = this.build_options(previous_page);
            this.render();
        },

        render: function () {
            let self = this;
            this.$('.o_content').html(QWeb.render(this.reportTemplate, {
                "widget": this,
                "options": self.options
            }))
        },
    });

    return ReportBaseAction;
})