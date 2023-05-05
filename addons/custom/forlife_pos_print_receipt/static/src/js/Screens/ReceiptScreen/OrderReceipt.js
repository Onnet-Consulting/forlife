odoo.define('forlife_pos_print_receipt.OrderReceipt', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');


    const CustomOrderReceipt = OrderReceipt =>class extends OrderReceipt {
        setup() {
            // FIXME:  set template respectively base on this.env.pos brand here
            // this.template = ...
            let y = 2;
            super.setup();
            let x = 1;
        }
    }

    Registries.Component.extend(OrderReceipt, CustomOrderReceipt);
});