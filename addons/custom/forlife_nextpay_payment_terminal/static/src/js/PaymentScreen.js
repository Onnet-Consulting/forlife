odoo.define('forlife_nextpay_payment_terminal.PaymentScreen', function (require) {
    'use strict';

    const {_t} = require('web.core');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const PosNextpayPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            setup() {
                super.setup();
                this.env.services.bus_service.addChannel(this._getNextPayChannelName());
                this.env.services.bus_service.addEventListener(
                    "notification",
                    this._on_payment_response_notification.bind(this)
                );
            }

            _getNextPayChannelName() {
                return JSON.stringify([
                    "nextpay_payment_response",
                    String(this.env.pos.config.id),
                ]);
            }

            _on_payment_response_notification({detail: notifications}) {
                if (!notifications) return false;
                const {payload, type} = notifications[0];
                if (type === "pos.config/nextpay_payment_response") {
                    return this._handle_nextpay_response(payload);
                }
                return false
            }

            // double check this function
            _handle_nextpay_response(payload) {
                const self = this;
                let order = this.currentOrder;
                const {orderId, transStatus, issuerCode, transCode} = payload;

                let selected_payment_line = order.get_paymentlines().filter((line) => {
                    return line.unique_id === orderId;
                })

                if (selected_payment_line.length > 0) {
                    selected_payment_line = selected_payment_line[0];
                    let current_payment_status = selected_payment_line.get_payment_status()
                    if (current_payment_status === 'done') return true;
                    if (current_payment_status === 'retry') return false;
                    if (transStatus === 100) {
                        selected_payment_line.set_payment_status('done');
                        selected_payment_line.transaction_id = transCode;
                        selected_payment_line.card_type = issuerCode;
                    } else {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('NextPay payment terminal'),
                            body: this.env._t("Something went wrong, can't finish the payment on NextPay payment terminal"),
                        });
                        selected_payment_line.set_payment_status('retry');
                    }
                }
            }


            /**
             * Finish any pending input before trying to validate.
             *
             * @override
             */
            // async validateOrder(isForceValidate) {
            //     NumberBuffer.capture();
            //     return super.validateOrder(...arguments);
            // }

            /**
             * Finish any pending input before sending a request to a terminal.
             *
             * @override
             */

            async _sendPaymentRequest({detail: line}) {
                NumberBuffer.capture();
                await super._sendPaymentRequest(...arguments);
                line.set_payment_status('waitingCapture');
            }

            /**
             * @override
             */
            // deletePaymentLine(event) {
            //     const {cid} = event.detail;
            //     const line = this.paymentLines.find((line) => line.cid === cid);
            //     if (line.mercury_data) {
            //         this.do_reversal(line, false);
            //     } else {
            //         super.deletePaymentLine(event);
            //     }
            // }

        };

    Registries.Component.extend(PaymentScreen, PosNextpayPaymentScreen);

    return PaymentScreen;
});
