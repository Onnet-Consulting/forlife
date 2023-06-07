odoo.define('forlife_point_of_sale.CustomReceiptScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl;

    const CustomReceiptScreen = ReceiptScreen => class extends ReceiptScreen {

            async _addNewOrder() {
                super._addNewOrder();
                if (this.partnerToNewOrder) {
                    await this.env.pos.selectedOrder.set_partner(this.partnerToNewOrder);
                };
            }

            setPartnerToNewOrder() {
                this.partnerToNewOrder = this.partnerToNewOrder ? false : this.currentOrder.get_partner();
                this.togglePartner();
            }

            togglePartner() {
                let result = Boolean(this.partnerToNewOrder);
                let node = $('#button-set-partner');
                if (result) {
                    node.addClass('highlight');
                } else {
                    node.removeClass('highlight');
                }
            }

    };

    Registries.Component.extend(ReceiptScreen, CustomReceiptScreen);
    return ReceiptScreen;
});