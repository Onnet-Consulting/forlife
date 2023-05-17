odoo.define('forlife_pos_product_change_refund.CustomOrderline', function(require) {
    'use strict';

    const CustomOrderline = require('forlife_pos_layout.CustomOrderline');
    const Registries = require('point_of_sale.Registries');

    const CustomOrderlinePointOrder = CustomOrderline => class extends CustomOrderline {
        getTotalDiscount() {
            var total = super.getTotalDiscount(...arguments);
            if(this.props.line.money_reduce_from_product_defective > 0){
                total += this.props.line.money_reduce_from_product_defective
            }
            return total;
        }

    }
    Registries.Component.extend(CustomOrderline, CustomOrderlinePointOrder);

    return CustomOrderline;
});
