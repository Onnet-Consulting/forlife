odoo.define('forlife_payment_terminal_base.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");

    const PaymentTerminalScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            setup() {
                super.setup();
                useListener('set-done-manually', this.setDonePaymentLineManually);
                this.env.services.bus_service.addEventListener(
                    "notification",
                    this._on_notification.bind(this)
                );
            }

            _on_notification({detail: notifications}) {
                if (!notifications) return false;
                for (const {payload, type} of notifications) {
                    this._handle_notification_payload(type, payload)
                }
                return true;
            }

            /**
             * Handle notification according to the 'type' and 'payload'
             *
             * @param type: notification type
             * @param payload: notification data
             */
            _handle_notification_payload(type, payload) {
            }

            setDonePaymentLineManually() {
                let line = this.selectedPaymentLine;
                line.set_payment_status('done');
            }

        };

    Registries.Component.extend(PaymentScreen, PaymentTerminalScreen);

    return PaymentScreen;
});
