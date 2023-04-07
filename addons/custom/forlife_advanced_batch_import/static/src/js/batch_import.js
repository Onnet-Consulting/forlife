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
            return import_options
        },
        call_import: function (kwargs) {
            console.log("zoooooooooooooooooooooooooooooooooooooo")
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
                if (results) {
                    window.open(
                        results,
                        '_blank' // <- This is what makes it open in a new window.
                    );
                } else {
                    this.trigger_up('warning', {title: _t('Something error !')});
                }

            });
        }
    });
});
