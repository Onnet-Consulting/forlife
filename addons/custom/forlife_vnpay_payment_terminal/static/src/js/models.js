odoo.define('forlife_vnpay_payment_terminal.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PosVNPayPayment = (Payment) => class PosVNPayPayment extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.vnpay_received_response = false;
            this.vnpay_sent_payment = false;
            this.vnpay_waiting_transaction_response_timeout = false;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.vnpay_received_response = json.vnpay_received_response;
            this.vnpay_sent_payment = json.vnpay_sent_payment;
            if (json.vnpay_waiting_transaction_response_timeout) {
                clearTimeout(json.vnpay_waiting_transaction_response_timeout);
            }
        }

        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                vnpay_received_response: this.vnpay_received_response,
                vnpay_sent_payment: this.vnpay_sent_payment,
                vnpay_waiting_transaction_response_timeout: this.vnpay_waiting_transaction_response_timeout
            });
        }
    }

    Registries.Model.extend(Payment, PosVNPayPayment);

    
});
