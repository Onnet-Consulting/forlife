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

            get_payment_line_by_unique_id(unique_id) {
                try {
                    let data = unique_id.split('_');
                    if (data.length !== 3) {
                        return false;
                    }
                    let order_uid = data[1];

                    // because cashier be able to switch between order,
                    // so we cannot get the correct order by calling this.currentOrder
                    let order_of_payment_line = _.find(this.env.pos.get_order_list(), order => {
                        return order.uid === order_uid;
                    })
                    if (!order_of_payment_line) return false;
                    return _.find(order_of_payment_line.get_paymentlines(), payment_line => {
                        return payment_line.unique_id === unique_id;
                    })
                } catch (err) {
                    return false
                }

            }

        };

    Registries.Component.extend(PaymentScreen, PaymentTerminalScreen);

    return PaymentScreen;
});
