odoo.define('forlife_pos_layout.OrderSummary', function(require) {
    'use strict';
    const OrderSummary = require('point_of_sale.OrderSummary');
    const Registries = require('point_of_sale.Registries');

    const OrderSummaryCustom = OrderSummary => class extends OrderSummary {
        getTotalQuantity() {
            var total = 0;
            const orderlines = this.props.order.orderlines;
            for (const orderline of orderlines) {
                total += orderline.get_quantity();
            }
            return total;
        }

        getTotalPriceWithTax() {
            var total = 0;
            const orderlines = this.props.order.orderlines;
            for (const orderline of orderlines) {
                total += orderline.get_price_with_tax();
            }
            return total;
        }
    }
    Registries.Component.extend(OrderSummary, OrderSummaryCustom);

    return OrderSummary;
});
