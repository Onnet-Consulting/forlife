odoo.define('advanced_batch_import.import', function (require) {
    "use strict";
    var core = require('web.core');
    var BaseImport = require('base_import.import')

    var _t = core._t;

    BaseImport.DataImport.include({
        import_options: function () {
            var self = this;
            var import_options = self._super.apply(this);
            import_options['base_import_id'] = self.id;
            import_options['split_file'] = parseInt(this.$('#oe_import_split_file').val() || 0);
            import_options['with_delay'] = parseInt(this.$('#oe_import_eta_time').val() || 0);
            import_options['sheet_name'] = this.$('#oe_import_sheet').val() || "Sheet1";
            return import_options
        },
        call_import: function (kwargs) {
            var self = this;
            // case validate , not truly import
            if (kwargs.dryrun) {
                return self._super.apply(this, arguments);
            } else {
                //case truly import
                var batch_import_checked = this.$('#oe_import_advanced_batch_import').prop('checked')
                console.log(batch_import_checked)
                if (!batch_import_checked) {
                    return self._super.apply(this, arguments);
                } else {
                    var fields = this.$('input.oe_import_match_field').map(function (index, el) {
                        return $(el).select2('val') || false;
                    }).get();
                    var columns = this.$('.o_import_header_name').map(function () {
                        return $(this).text().trim().toLowerCase() || false;
                    }).get();
                    var tracking_disable = false
                    kwargs.context = _.extend(
                        {}, this.parent_context,
                        {
                            tracking_disable: tracking_disable,
                            base_import_id: this.id
                        }
                    );
                    this.importStartTime = Date.now();
                    this.stopImport = false;
                    this.batchSize = parseInt(this.$('#oe_import_batch_limit').val() || 0);
                    var opts = this.import_options();
                    return this.create_parent_batch_import(opts, [this.id, fields, columns], kwargs)

                }

            }
        },
        create_parent_batch_import: function (opts, args, kwargs) {
            var self = this;
            opts.callback && opts.callback(this);
            return this._rpc({
                model: 'parent.batch.import',
                method: 'create_parent_batch_import',
                args: args.concat([opts]),
                kwargs: kwargs
            }, {
                shadow: true,
            }).then(function (results) {
                console.log(results);
                if (results) {
                    // return Promise.resolve({
                    //     'messages': [{
                    //         type: 'info',
                    //         record: false,
                    //         message: "Queue Job batch import created , follow url : ".concat(results),
                    //         url: results,
                    //     }]
                    // });
                    window.open(
                        results,
                        '_self' // <- This is what makes it open in a new window.
                    );
                } else {
                    this.trigger_up('warning', {title: _t('Something error !')});
                }

            });

        },
        onimport: function () {
            var self = this;
            var prom = this.call_import({dryrun: false});
            var batch_import_checked = this.$('#oe_import_advanced_batch_import').prop('checked')
            if (!batch_import_checked) {
                prom.then(function (results) {
                    if (self.stopImport) {
                        var recordsImported = results.ids ? results.ids.length : 0;
                        if (recordsImported) {
                            self.$('#oe_import_row_start').val((results.skip || 0) + 1);
                            self.displayNotification({
                                message: _.str.sprintf(
                                    _t("%d records successfully imported"),
                                    recordsImported
                                )
                            });
                        }
                        self['import_interrupted'](results);
                    } else if (!_.any(results.messages, function (message) {
                        return message.type === 'error';
                    })) {
                        self['import_succeeded'](results);
                        return;
                    }
                    self['import_failed'](results);
                });
                return prom;
            } else {
                prom.then(this.proxy('validated'));
                return prom;
            }
        },

    });
});
