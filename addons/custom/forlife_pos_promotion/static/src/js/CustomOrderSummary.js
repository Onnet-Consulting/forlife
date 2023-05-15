odoo.define('forlife_pos_promotion.CustomOrderSummary', function(require) {
    'use strict';
    const CustomOrderSummary = require('forlife_pos_layout.CustomOrderSummary');
    const Registries = require('point_of_sale.Registries');

    const CustomOrderSummaryPromotion = CustomOrderSummary => class extends CustomOrderSummary {

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
    Registries.Component.extend(CustomOrderSummary, CustomOrderSummaryPromotion);

    return CustomOrderSummary;
});
