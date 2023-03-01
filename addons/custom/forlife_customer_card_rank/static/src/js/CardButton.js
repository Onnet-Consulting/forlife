/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class CardButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        const order = this.env.pos.get_order();
        const current_rank = order.partner.card_rank_by_brand[this.env.pos.pos_branch[0].id];
        order.card_rank_program = this.env.pos.card_rank_program_by_rank_id[current_rank[0]];
    }
}

CardButton.template = 'CardButton';

ProductScreen.addControlButton({
    component: CardButton,
    condition: function () {
        return this.partner && this.partner.card_rank_by_brand[this.env.pos.pos_branch[0].id] && this.env.pos.get_order().orderlines.length > 0;
    }
});

Registries.Component.add(CardButton);
