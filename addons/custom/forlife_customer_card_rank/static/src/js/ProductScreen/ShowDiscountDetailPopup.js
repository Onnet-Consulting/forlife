odoo.define('forlife_customer_card_rank.ShowDiscountDetailPopup', function (require) {
    "use strict";

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const {useState} = owl;

    class ShowDiscountDetailPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
        }

        cancel() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: false, payload: null},
            });
        }

        confirm() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: true, payload: this.actionApply()},
            });
        }

        actionApply() {
            return true;
        }

    }

    ShowDiscountDetailPopup.template = "ShowDiscountDetailPopup";
    Registries.Component.add(ShowDiscountDetailPopup);

    return ShowDiscountDetailPopup;
})