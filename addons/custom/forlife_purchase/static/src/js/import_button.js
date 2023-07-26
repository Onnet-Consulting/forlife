odoo.define('module-name.tree_button', function (require) {
    "use strict";
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var TreeButton = ListController.extend({
        buttons_template: 'import.production.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .import_your_action': '_OpenWizard',
        }),
        _OpenWizard: function () {
            return this.do_action('forlife_purchase.import_production_from_excel_action');
        }
    });
    var InputListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: TreeButton,
        }),
    });
    viewRegistry.add('button_import_in_tree', InputListView);
});