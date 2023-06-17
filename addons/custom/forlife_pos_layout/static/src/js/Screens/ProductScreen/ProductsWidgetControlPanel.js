odoo.define('forlife_pos_layout.ProductsWidgetControlPanel', function(require) {
    'use strict';
    const ProductsWidgetControlPanel = require('point_of_sale.ProductsWidgetControlPanel');
    const Registries = require('point_of_sale.Registries');
    const CustomProductsWidgetControlPanel = (ProductsWidgetControlPanel) =>
        class extends ProductsWidgetControlPanel {
            updateSearch(event) {
                this.trigger('update-search', event.target.value);
            }
            async _onPressEnterKey() {
                if (!this.searchWordInput.el.value) return;
                this.trigger('update-search', event.target.value);
            }

        }
    Registries.Component.extend(ProductsWidgetControlPanel,CustomProductsWidgetControlPanel);

    return ProductsWidgetControlPanel;


})