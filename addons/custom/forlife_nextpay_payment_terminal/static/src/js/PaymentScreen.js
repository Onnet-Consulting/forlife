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
            }

            _getNextPayChannelName() {
                return JSON.stringify([
                    "nextpay_payment_response",
                    String(this.env.pos.config.id),
                ]);
            }

            _handle_notification_payload(type, payload) {
                super._handle_notification_payload(...arguments);
                if (type === "pos.config/nextpay_payment_response") {
                    this._handle_nextpay_transaction_result_response(payload);
                }
            }

            _handle_nextpay_transaction_result_response(payload) {
                const self = this;
                let order = this.currentOrder;
                const {orderId, transStatus, issuerCode, transCode} = payload;

                let selected_payment_line = order.get_paymentlines().filter((line) => {
                    return line.unique_id === orderId;
                })
                selected_payment_line.nextpay_received_response = true;

                if (selected_payment_line.length > 0) {
                    selected_payment_line = selected_payment_line[0];
                    clearTimeout(selected_payment_line.nextpay_waiting_transaction_response_timeout);
                    let current_payment_status = selected_payment_line.get_payment_status()
                    // prevent handle response repeatedly
                    if (selected_payment_line.nextpay_received_response && ['done', 'retry'].includes(current_payment_status)) return true;
                    if (transStatus === 100) {
                        selected_payment_line.set_payment_status('done');
                        selected_payment_line.transaction_id = transCode;
                        selected_payment_line.card_type = issuerCode;
                    } else {
                        this.showPopup('ErrorPopup', {
                            title: _t('NextPay Error'),
                            body: _t("Something went wrong, can't finish the payment on NextPay payment terminal"),
                        });
                        selected_payment_line.set_payment_status('retry');
                    }
                }
            }


            async _sendPaymentRequest({detail: line}) {
                NumberBuffer.capture();
                await super._sendPaymentRequest(...arguments);
                if (line.payment_method.use_payment_terminal === 'nextpay') {
                    line.set_payment_status('waitingCapture');
                }
            }

        };

    Registries.Component.extend(PaymentScreen, PosNextpayPaymentScreen);

    return PaymentScreen;
});
