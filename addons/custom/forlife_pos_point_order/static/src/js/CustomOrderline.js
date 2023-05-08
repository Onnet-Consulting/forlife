odoo.define('forlife_pos_point_order.CustomOrderline', function(require) {
    'use strict';

    const CustomOrderline = require('forlife_pos_layout.CustomOrderline');
    const Registries = require('point_of_sale.Registries');

    const CustomOrderlinePointOrder = CustomOrderline => class extends CustomOrderline {
        getTotalDiscount() {
            var total = super.getTotalDiscount(...arguments);
            if (this.props.line.point) {
                total += Math.abs(this.props.line.point);
            }
            return total;
        }

    }
    Registries.Component.extend(CustomOrderline, CustomOrderlinePointOrder);

    return CustomOrderline;
});
