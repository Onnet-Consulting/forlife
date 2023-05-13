odoo.define('forlife_pos_promotion.OrderSummary', function(require) {
    'use strict';
    const OrderSummary = require('point_of_sale.OrderSummary');
    const Registries = require('point_of_sale.Registries');

    const OrderSummaryPromotion = OrderSummary => class extends OrderSummary {

        getTotalPriceWithTax() {
            var total = super.getTotalPriceWithTax(...arguments);
            const order = this.props.order;
            const orderlines = order.orderlines;
            for (const orderline of orderlines) {
                if (orderline.is_applied_promotion()) {
                    const applied_promotions = orderline.get_applied_promotion_str();
                    for (const applied_promotion of applied_promotions) {
                        total += applied_promotion.discount_amount;
                    }
                }
            }
            return total;
        }

    }
    Registries.Component.extend(OrderSummary, OrderSummaryPromotion);

    return OrderSummary;
});
