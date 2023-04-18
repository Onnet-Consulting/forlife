odoo.define('forlife_nextpay_payment_terminal.models', function (require) {
    const models = require('point_of_sale.models');
    const PaymentNextPay = require('forlife_nextpay_payment_terminal.payment');

    models.register_payment_method('nextpay', PaymentNextPay);
});
