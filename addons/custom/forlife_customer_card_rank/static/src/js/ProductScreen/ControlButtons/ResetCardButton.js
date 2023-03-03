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
        const order = this.env.pos.get_order();
        order.card_rank_program = null;
        order.card_rank_applied = false;
        for (let line of order.orderlines) {
            line.action_reset_card_rank();
        }
    }
}

ResetCardButton.template = 'ResetCardButton';

ProductScreen.addControlButton({
    component: ResetCardButton, position: ['after', 'RefundButton'], condition: function () {
        return this.env.pos.get_order().card_rank_applied;
    }
});

Registries.Component.add(ResetCardButton);
