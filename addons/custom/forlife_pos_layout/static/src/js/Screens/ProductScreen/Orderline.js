odoo.define('forlife_pos_layout.CustomOrderline', function(require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');

    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    class CustomOrderline extends Orderline {
        getTotalDiscount() {
            return 0;
        }

        getPercentDiscount() {
            var percent_discount = 0;
            var discount = this.getTotalDiscount();
            var unit_price = this.props.line.get_unit_display_price();
            if (unit_price !== 0) {
                percent_discount = (discount / unit_price) * 100;
            }
            return round_pr(percent_discount, this.env.pos.currency.rounding);
        }
    }
    CustomOrderline.template = 'CustomOrderline';

    Registries.Component.add(CustomOrderline);

    return CustomOrderline;
});
