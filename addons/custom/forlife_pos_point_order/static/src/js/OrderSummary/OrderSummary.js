odoo.define('forlife_pos_point_order.OrderSummaryPoint', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    const OrderSummary = require('point_of_sale.OrderSummary');
    const { float_is_zero } = require('web.utils');


    const OrderSummaryPoint = OrderSummary => class extends OrderSummary {
         getTax() {
            const total = this.props.order.get_total_with_tax();
            const totalWithoutTax = this.props.order.get_total_without_tax() - this.props.order.get_total_point_without_tax();
            const taxAmount = total - totalWithoutTax;
            return {
                hasTax: !float_is_zero(taxAmount, this.env.pos.currency.decimal_places),
                displayAmount: this.env.pos.format_currency(taxAmount),
            };
        }
    }

    Registries.Component.extend(OrderSummary, OrderSummaryPoint);

    return OrderSummaryPoint;

});