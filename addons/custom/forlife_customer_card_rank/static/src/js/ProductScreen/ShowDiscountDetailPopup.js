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
            let self = this;
            for (let line of self.props.order_lines){
                line.apply_cr_discount = [...$('.discount-detail-checkbox')].find(item => item.id == line.id).checked;
            }
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: true, payload: null},
            });
        }
    }

    ShowDiscountDetailPopup.template = "ShowDiscountDetailPopup";
    Registries.Component.add(ShowDiscountDetailPopup);

    return ShowDiscountDetailPopup;
})