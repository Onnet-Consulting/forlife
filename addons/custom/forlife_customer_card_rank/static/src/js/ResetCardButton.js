/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class ResetCardButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        console.log('ResetCardButton');
    }
}

ResetCardButton.template = 'ResetCardButton';

ProductScreen.addControlButton({
    component: ResetCardButton,
    condition: function () {
        return this.partner;
    }
});

Registries.Component.add(ResetCardButton);
