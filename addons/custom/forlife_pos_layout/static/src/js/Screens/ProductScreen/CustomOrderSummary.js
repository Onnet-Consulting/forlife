odoo.define('forlife_pos_layout.CustomOrderSummary', function(require) {
    'use strict';

    const OrderSummary = require('point_of_sale.OrderSummary');
    const Registries = require('point_of_sale.Registries');

    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    class CustomOrderSummary extends OrderSummary {
        getTotalQuantity() {
            var total = 0;
            const orderlines = this.props.order.orderlines;
            for (const orderline of orderlines) {
                total += orderline.get_quantity();
            }
            return total;
        }

        // Tổng tiền hàng
        getTotalPriceWithTax() {
            // lấy số tiền ban đầu có
            var total = 0;
            // lấy số tiền đã giảm thủ công
            var totalDiscount = 0;
            var rounding = this.props.order.pos.currency.rounding;
            const orderlines = this.props.order.orderlines;
            for (const orderline of orderlines) {
                total += orderline.get_price_with_tax();
                if(orderline.money_reduce_from_product_defective >0){
                    total += orderline.money_reduce_from_product_defective;
                }
                totalDiscount += round_pr(orderline.get_unit_price() * orderline.get_quantity() * (orderline.get_discount()/100), rounding);
            }
            return total + totalDiscount;
        }

        // tổng tiền thanh toán
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
