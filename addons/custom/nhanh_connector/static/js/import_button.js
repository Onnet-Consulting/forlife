odoo.define('nhanh_connector.tree_button', function (require) {
    "use strict";
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var TreeButton = ListController.extend({
        buttons_template: 'import.nhanh.connector.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .import_your_action': '_OpenWizard',
        }),
        _OpenWizard: function () {
            return this.do_action('nhanh_connector.import_transport_from_excel_action');
        }
    });
    var InputListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: TreeButton,
        }),
    });
    viewRegistry.add('button_import_nhanh_connector', InputListView);
});