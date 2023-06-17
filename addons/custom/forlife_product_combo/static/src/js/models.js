odoo.define('forlife_product_combo.models', function (require) {
    "use strict";

    var {PosGlobalState} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const ProductComboPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.product_combo = loadedData['product_combo'];
        }
    }
    Registries.Model.extend(PosGlobalState, ProductComboPosGlobalState);

});
