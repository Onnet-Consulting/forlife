odoo.define('forlife_nextpay_payment_terminal.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PosNextPayPayment = (Payment) => class PosNextPayPayment extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.nextpay_received_response = false;
            this.nextpay_sent_payment = false;
            this.nextpay_waiting_transaction_response_timeout = false;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.nextpay_received_response = json.nextpay_received_response;
            this.nextpay_sent_payment = json.nextpay_sent_payment;
            if (json.nextpay_waiting_transaction_response_timeout) {
                clearTimeout(json.nextpay_waiting_transaction_response_timeout);
            }
        }

        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                nextpay_received_response: this.nextpay_received_response,
                nextpay_sent_payment: this.nextpay_sent_payment,
                nextpay_waiting_transaction_response_timeout: this.nextpay_waiting_transaction_response_timeout
            });
        }
    }

    Registries.Model.extend(Payment, PosNextPayPayment);

    
});
