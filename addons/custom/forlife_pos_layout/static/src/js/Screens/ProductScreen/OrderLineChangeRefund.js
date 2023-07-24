odoo.define('forlife_pos_layout.OrderlineChangeRefund', function(require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');

    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    class OrderlineChangeRefund extends Orderline {
        getTotalDiscount() {
            return 0;
        }

        getPercentDiscountManual() {
            return this.props.line.get_discount();
        }
        getTotalDiscountManual() {
            var rounding = this.props.line.pos.currency.rounding;
            return round_pr(this.props.line.get_unit_price() * this.props.line.get_quantity() * (this.props.line.get_discount()/100), rounding);
        }

        getTotalDiscountSingleManual() {
            var rounding = this.props.line.pos.currency.rounding;
            return round_pr(this.props.line.get_unit_price() * (this.props.line.get_discount()/100), rounding);
        }

        getPercentDiscount() {
            var percent_discount = 0;
            var discount = this.getTotalDiscount();
            var unit_price = this.props.line.original_price;
            var quantity = this.props.line.get_quantity();
            if (unit_price !== 0 && quantity !== 0) {
                percent_discount = ((discount / quantity) / unit_price) * 100;
            }
            return Math.round(percent_discount * 100) / 100;
        }
    }
    OrderlineChangeRefund.template = 'OrderlineChangeRefund';

    Registries.Component.add(OrderlineChangeRefund);

    return OrderlineChangeRefund;
});
