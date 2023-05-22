odoo.define('forlife_pos_layout.CustomOrderSummary', function(require) {
    'use strict';

    const OrderSummary = require('point_of_sale.OrderSummary');
    const Registries = require('point_of_sale.Registries');

    var utils = require('web.utils');

    class CustomOrderSummary extends OrderSummary {
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
                if(orderline.money_reduce_from_product_defective >0){
                    total += orderline.money_reduce_from_product_defective;
                }
            }
            return total;
        }
        getTotalNotFormat() {
            return this.props.order.get_total_with_tax();
        }

        getTotalDiscountCustomDefective() {
            var total = 0;
            const orderlines = this.props.order.orderlines;
            for (const orderline of orderlines) {
                total += orderline.getTotalDiscountLineDefective();
            }
            return total;
        }
    }
    CustomOrderSummary.template = 'CustomOrderSummary';

    Registries.Component.add(CustomOrderSummary);

    return CustomOrderSummary;
});
