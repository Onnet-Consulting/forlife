odoo.define('forlife_pos_print_receipt.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const CustomPaymentScreen = PaymentScreen => class extends PaymentScreen {
        async showOrderNotePopup() {
            const current_order = this.env.pos.get_order();
            if (!current_order) return;
            const {confirmed, payload: inputNote} = await this.showPopup('TextAreaPopup', {
                startingValue: current_order.get_note(),
                title: this.env._t('Add Order Note'),
            });
            if (confirmed) {
                current_order.set_note(inputNote);
            }
        }
    }

    Registries.Component.extend(PaymentScreen, CustomPaymentScreen);
});