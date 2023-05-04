odoo.define('forlife_pos_print_receipt.OrderReceipt', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');


    const CustomOrderReceipt = OrderReceipt =>class extends OrderReceipt {
        setup() {
            // FIXME:  set template respectively base on this.env.pos brand here
            // this.template = ...
            super.setup();
        }
    }

    Registries.Component.extend(OrderReceipt, CustomOrderReceipt);
});