odoo.define('forlife_nextpay_payment_terminal.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const {Order} = require('point_of_sale.models');

    const PosNextPayPayment = (Payment) => class PosNextPayPayment extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.nextpay_received_response = false;
            this.nextpay_sent_payment = false;
            this.nextpay_waiting_transaction_response_timeout = false;
            this.transaction_timeout = 60000;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.nextpay_received_response = json.nextpay_received_response;
            this.nextpay_sent_payment = json.nextpay_sent_payment;
            this.init_nextpay_transaction_response_timeout();
        }

        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                nextpay_received_response: this.nextpay_received_response,
                nextpay_sent_payment: this.nextpay_sent_payment,
            });
        }

        init_nextpay_transaction_response_timeout() {
            clearTimeout(this.nextpay_waiting_transaction_response_timeout);
            const self = this;
            if (this.get_payment_status() === 'waitingCapture' && this.nextpay_sent_payment) {
                this.nextpay_waiting_transaction_response_timeout = setTimeout(function () {
                    self.set_payment_status('done');
                }, self.transaction_timeout)
            }
        }
    }

    Registries.Model.extend(Payment, PosNextPayPayment);

    const PosNextPayModel = (Order) =>
        class PosNextPayModel extends Order {
            /* ---- Payment Lines --- */
            add_paymentline(payment_method) {
                const newPaymentline = super.add_paymentline(payment_method);
                if (payment_method.use_payment_terminal === "nextpay" && this.selected_paymentline.get_amount() < 0) {
                    newPaymentline.set_payment_status('done');
                }

                return newPaymentline;
            }
        }

    Registries.Model.extend(Order, PosNextPayModel);
});
