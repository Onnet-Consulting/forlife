/** @odoo-module **/

import Registries from 'point_of_sale.Registries';
import RefundButton from 'point_of_sale.RefundButton';
const { useListener } = require("@web/core/utils/hooks");

export const CustomRefundButton = (RefundButton) =>
    class extends RefundButton {
        setup() {
            super.setup();
            // useListener('click', this._onClick);
            console.log('extend refund ok ????')
        }
    }

Registries.Component.extend(RefundButton, CustomRefundButton);
