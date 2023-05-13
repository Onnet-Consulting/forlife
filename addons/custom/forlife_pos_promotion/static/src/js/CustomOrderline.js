odoo.define('forlife_pos_promotion.CustomOrderline', function(require) {
    'use strict';

    const CustomOrderline = require('forlife_pos_layout.CustomOrderline');
    const Registries = require('point_of_sale.Registries');

    const CustomOrderlinePromotion = CustomOrderline => class extends CustomOrderline {
        getTotalDiscount() {
            var total = super.getTotalDiscount(...arguments);
            const applied_promotions = this.props.line.get_applied_promotion_str();
            for (const applied_promotion of applied_promotions) {
                if (applied_promotion) {
                    total += applied_promotion.discount_amount;
                }
            }
            return total;
        }

        getPercentDiscount() {
            if (this.props.line.is_applied_promotion()) {
                var percent_discount = 0;
                var discount = this.getTotalDiscount();
                var original_price = this.props.line.original_price;
                var quantity = this.props.line.get_quantity();
                if (original_price !== 0 && quantity !== 0) {
                    percent_discount = ((discount / quantity) / original_price) * 100;
                }
                return Math.round(percent_discount * 100) / 100;
            }
            else {
                return super.getPercentDiscount(...arguments);
            }
        }

    }
    Registries.Component.extend(CustomOrderline, CustomOrderlinePromotion);

    return CustomOrderline;
});
