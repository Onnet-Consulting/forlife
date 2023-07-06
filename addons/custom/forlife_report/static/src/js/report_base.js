odoo.define('forlife_report.report_base', function (require) {
    'use strict';

    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const {round_decimals: round_di} = require('web.utils');
    const QWeb = core.qweb;
    const _t = core._t;

    function format_decimal(amount, precision = 0) {
        if (typeof amount === 'number') {
            amount = round_di(amount, precision).toFixed(precision);
        }

        return amount;
    }

    let ReportBaseAction = AbstractAction.extend({
        events: {
            'click button.o_pager_next': 'next_page',
            'click button.o_pager_previous': 'previous_page',
            'click .export_data': 'action_export_data',
            'click .btn_back': 'action_back',
        },
        readDataTimeout: 300,

        init: function (parent, action) {
            this.actionManager = parent;
            this.odoo_context = action.context;
            this.report_model = this.odoo_context.report_model || this.odoo_context.active_model || action.params.active_model;
            this.report_id = this.odoo_context.active_id || action.params.active_id;
            this.func = {
                format_decimal
            };
            return this._super.apply(this, arguments);
        },

        willStart: async function () {
            const reportPromise = this._rpc({
                model: this.report_model,
                method: 'get_data',
                args: [this.report_id, this.odoo_context.allowed_company_ids || []],
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
                data: this.data.slice(start_index, start_index + this.record_per_page),
            }
        },

        parse_data: function (data) {
            this.data = data.data;
            this.reportTitle = data.reportTitle;
            this.reportTemplate = data.reportTemplate;
            this.reportPager = data.reportPager;
            this.report_filename = data.reportTitle + '.xls';
            this.report_type_id = 'all_data';
            this.titles = data.titles;
            this.column_add = data.column_add;
            this.record_per_page = data.recordPerPage || this.data.length;
            this.total_records = this.data.length;
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

        action_export_data: function (e) {
            this.export_data_by_id(e.currentTarget.getAttribute('button-id'), e.currentTarget.getAttribute('filename'));
        },

        render: function () {
            let self = this;
            this.$('.o_content').html(QWeb.render(this.reportTemplate, {
                "widget": this,
                "options": self.options
            }));
        },

        export_data_by_id: function (id, filename) {
            var tableSelect = document.getElementById(id);
            if (!tableSelect) {
                alert(_.str.sprintf(_t("Data not found by id '%s'"), id));
            } else {
                var downloadLink = document.createElement("a");
                document.body.appendChild(downloadLink);
                downloadLink.href = 'data:application/vnd.ms-excel;charset=utf-8,' + encodeURI("\uFEFF" + tableSelect.outerHTML);
                downloadLink.download = filename;
                downloadLink.click();
            }
        },
        action_back: function () {
            window.history.back();
        }
    });

    const AvailableReportAction = AbstractAction.extend({
        reportTemplate: 'AvailableReport',

        willStart: async function () {
            const reportPromise = this._rpc({
                model: 'report.base',
                method: 'get_available_report',
                args: [],
                context: this.odoo_context
            }, {
                timeout: this.readDataTimeout,
            }).then(res => this.parse_data(res))
            const parentPromise = this._super(...arguments);
            return Promise.all([reportPromise, parentPromise]);
        },

        start: async function () {
            await this._super(...arguments);
            this.render();
        },

        parse_data: function (data) {
            this.report_info = data;
        },

        render: function () {
            let self = this;
            this.$('.o_content').html(QWeb.render(this.reportTemplate, {
                "widget": this,
            }));
        },
    })

    core.action_registry.add('available_report_action', AvailableReportAction)
    core.action_registry.add('report_base_action', ReportBaseAction)


    return ReportBaseAction;
})