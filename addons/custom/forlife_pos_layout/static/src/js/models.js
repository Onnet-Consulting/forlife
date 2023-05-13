odoo.define('forlife_pos_layout.models', function (require) {
    "use strict";

    var {PosGlobalState, Orderline, Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const LayoutOrderline = (Orderline) => class extends Orderline {
        constructor(obj, options) {
            super(...arguments);
        }

        get_display_price_after_discount() {
            return this.get_display_price();
        }
    }

    Registries.Model.extend(Orderline, LayoutOrderline);
});