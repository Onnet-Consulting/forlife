/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import {useListener} from "@web/core/utils/hooks";

export class ResetCardButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        this.env.pos.get_order().action_reset_card_rank_program();
    }
}

ResetCardButton.template = 'ResetCardButton';

ProductScreen.addControlButton({
    component: ResetCardButton, position: ['after', 'RefundButton'], condition: function () {
        return this.env.pos.get_order().card_rank_program;
    }
});

Registries.Component.add(ResetCardButton);
