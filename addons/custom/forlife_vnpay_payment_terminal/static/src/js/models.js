odoo.define('forlife_vnpay_payment_terminal.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const {Order} = require('point_of_sale.models');


    const PosVNPayPayment = (Payment) => class PosVNPayPayment extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.vnpay_received_response = false;
            this.vnpay_sent_payment = false;
            this.vnpay_waiting_transaction_response_timeout = false;
            this.transaction_timeout = 130000; // ~2' (VNPay send 1 request/per minute to Odoo IPN endpoint -> wait at least two request)
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.vnpay_received_response = json.vnpay_received_response;
            this.vnpay_sent_payment = json.vnpay_sent_payment;
            this.init_vnpay_transaction_response_timeout();
        }

        export_as_JSON() {
            clearTimeout(this.vnpay_waiting_transaction_response_timeout);
            return _.extend(super.export_as_JSON(...arguments), {
                vnpay_received_response: this.vnpay_received_response,
                vnpay_sent_payment: this.vnpay_sent_payment,
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

    const PosVNPayModel = (Order) =>
        class PosVNPayModel extends Order {
            /* ---- Payment Lines --- */
            add_paymentline(payment_method) {
                const newPaymentline = super.add_paymentline(payment_method);
                if (payment_method.use_payment_terminal === "vnpay" && this.selected_paymentline.get_amount() < 0) {
                    newPaymentline.set_payment_status('done');
                }

                return newPaymentline;
            }
        }

    Registries.Model.extend(Order, PosVNPayModel);

});
