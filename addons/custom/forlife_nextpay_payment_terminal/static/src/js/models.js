odoo.define('forlife_nextpay_payment_terminal.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PosNextPayPayment = (Payment) => class PosNextPayPayment extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.received_nextpay_response = false;
            this.sent_payment_to_nextpay = false;
            this.waiting_nextpay_transaction_response_timeout = false;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.received_nextpay_response = json.received_nextpay_response;
            this.sent_payment_to_nextpay = json.sent_payment_to_nextpay;
            if (json.waiting_nextpay_transaction_response_timeout) {
                clearTimeout(json.waiting_nextpay_transaction_response_timeout);
            }
        }

        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                received_nextpay_response: this.received_nextpay_response,
                sent_payment_to_nextpay: this.sent_payment_to_nextpay,
                waiting_nextpay_transaction_response_timeout: this.waiting_nextpay_transaction_response_timeout
            });
        }
    }

    Registries.Model.extend(Payment, PosNextPayPayment);

    
});
