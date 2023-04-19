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
                    this._onNotification.bind(this)
                );
            }

            _getNextPayChannelName() {
                return JSON.stringify([
                    "nextpay_payment_response",
                    this.env.pos.config.id,
                ]);
            }

            _onNotification({detail: notifications}) {
                let payloads = [];
                console.log('received data', notifications);
                for (const {payload, type} of notifications) {
                    if (type === "pos.config/payment_response") {
                        payloads.push(payload);
                    }
                }
                this._handleNotification(payloads);
            }

            _handleNotification(payloads) {
                // update payment line here
                console.log('ez=>>>>>>>>>>>>>>>')
                console.log(payloads)
                // this.on_nextpay_payment_transaction_update(payloads);
            }

            // double check this function
            on_nextpay_payment_transaction_update(data) {
                let self = this;
                let order = this.get_order();
                if (!this.gui) return false;
                let payment_screen = this.gui.screen_instances.payment

                let selected_payment_line = order.get_paymentlines().filter((line) => {
                    let payment_transaction_id = line.unique_id;
                    return payment_transaction_id === data.orderId;
                })

                if (selected_payment_line.length > 0) {
                    selected_payment_line = selected_payment_line[0];
                    let transaction_code = data.transStatus;
                    if (transaction_code === 100) {
                        selected_payment_line.set_payment_status('done');
                        selected_payment_line.transaction_id = data.orderId;
                        selected_payment_line.card_type = data.issuerCode || '';
                        payment_screen.render_paymentlines();
                    } else {
                        selected_payment_line.payment_method.payment_terminal._show_error("Something went wrong, please re-check on NextPay");
                        selected_payment_line.set_payment_status('retry');
                    }
                }
            }


            /**
             * Finish any pending input before trying to validate.
             *
             * @override
             */
            async validateOrder(isForceValidate) {
                NumberBuffer.capture();
                return super.validateOrder(...arguments);
            }

            /**
             * Finish any pending input before sending a request to a terminal.
             *
             * @override
             */
            async _sendPaymentRequest({detail: line}) {
                NumberBuffer.capture();
                return super._sendPaymentRequest(...arguments);
            }

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
