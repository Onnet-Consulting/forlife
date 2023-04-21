odoo.define('forlife_vnpay_payment_terminal.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosVNPayPayment = (Payment) => class PosVNPayPayment extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.vnpay_received_response = false;
            this.vnpay_sent_payment = false;
            this.vnpay_waiting_transaction_response_timeout = false;
            this.vnpay_show_manually_done_button = false;
            this.transaction_timeout = 2000; // ~2' (VNPay send 1 request/per minute to Odoo IPN endpoint -> wait at least two request)
            // this.transaction_timeout = 130000; // ~2' (VNPay send 1 request/per minute to Odoo IPN endpoint -> wait at least two request)
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.vnpay_received_response = json.vnpay_received_response;
            this.vnpay_sent_payment = json.vnpay_sent_payment;
            this.init_vnpay_transaction_response_timeout()
            this.vnpay_show_manually_done_button = json.vnpay_show_manually_done_button;
        }

        export_as_JSON() {
            clearTimeout(this.vnpay_waiting_transaction_response_timeout);
            return _.extend(super.export_as_JSON(...arguments), {
                vnpay_received_response: this.vnpay_received_response,
                vnpay_sent_payment: this.vnpay_sent_payment,
                vnpay_show_manually_done_button: this.vnpay_show_manually_done_button,
            });
        }

        init_vnpay_transaction_response_timeout() {
            clearTimeout(this.vnpay_waiting_transaction_response_timeout);
            const self = this;
            if (this.get_payment_status() === 'waitingCapture' && this.vnpay_sent_payment) {
                this.vnpay_waiting_transaction_response_timeout = setTimeout(function () {
                    self.set_payment_status('done');
                }, self.transaction_timeout)
            }
        }
    }

    Registries.Model.extend(Payment, PosVNPayPayment);


});
