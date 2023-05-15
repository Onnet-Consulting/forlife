odoo.define('forlife_customer_card_rank.CustomOrderline', function(require) {
    'use strict';

    const CustomOrderline = require('forlife_pos_layout.CustomOrderline');
    const Registries = require('point_of_sale.Registries');

    const CustomOrderlineCardRank = CustomOrderline => class extends CustomOrderline {
        getTotalDiscount() {
            var total = super.getTotalDiscount(...arguments);
            return total += this.props.line.get_card_rank_discount();
        }

    }
    Registries.Component.extend(CustomOrderline, CustomOrderlineCardRank);

    return CustomOrderline;
});
