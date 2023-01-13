odoo.define('forlife_pos_payment_change.PaymentChangePopupLine', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentChangePopupLine extends PosComponent {
    }
    PaymentChangePopupLine.template = 'PaymentChangePopupLine';

    Registries.Component.add(PaymentChangePopupLine);

    return PaymentChangePopupLine;
});
