odoo.define('forlife_vnpay_payment_terminal.PaymentScreen', function (require) {
    'use strict';

    const {_t} = require('web.core');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');


    const PosVNPayPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            setup() {
                super.setup();
                this.env.services.bus_service.addChannel(this._getVNPayChannelName());
            }

            _getVNPayChannelName() {
                return JSON.stringify([
                    "vnpay_payment_response",
                    String(this.env.pos.config.id),
                ]);
            }

            _handle_notification_payload(type, payload) {
                super._handle_notification_payload(...arguments);
                if (type === "pos.config/vnpay_payment_response") {
                    this._handle_vnpay_transaction_result_response(payload);
                }
            }

            _handle_vnpay_transaction_result_response(payload) {
                let selected_payment_line = this.get_payment_line_by_unique_id(orderId);
                const {responseCode, transactionCode, bankCode, responseMessage} = payload;

                if (selected_payment_line) {
                    clearTimeout(selected_payment_line.vnpay_waiting_transaction_response_timeout);
                    selected_payment_line.vnpay_received_response = true;
                    let current_payment_status = selected_payment_line.get_payment_status()
                    if (selected_payment_line.vnpay_received_response && ['done', 'retry'].includes(current_payment_status)) return true;
                    if (responseCode === '200') {
                        selected_payment_line.set_payment_status('done');
                        selected_payment_line.transaction_id = transactionCode;
                        selected_payment_line.card_type = bankCode || '';
                    } else {
                        this.showPopup('ErrorPopup', {
                            title: _t('VNPay Error'),
                            body: responseMessage,
                        });
                        selected_payment_line.set_payment_status('retry');
                    }
                }
            }

            async _sendPaymentRequest({detail: line}) {
                NumberBuffer.capture();
                await super._sendPaymentRequest(...arguments);
                if (line.payment_method.use_payment_terminal === 'vnpay') {
                    line.set_payment_status('waitingCapture');
                }
            }

        };

    Registries.Component.extend(PaymentScreen, PosVNPayPaymentScreen);

    return PaymentScreen;
});
