/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import {useListener} from "@web/core/utils/hooks";

const {Gui} = require('point_of_sale.Gui');
const core = require('web.core');
const _t = core._t;

export class CardButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        const order = this.env.pos.get_order();
        const current_rank = order.partner.card_rank_by_brand[this.env.pos.pos_branch[0].id];
        const card_rank_program = this.env.pos.card_rank_program_by_rank_id[current_rank[0]];
        if (!card_rank_program) {
            await Gui.showPopup('ErrorPopup', {
                'title': _t("Card Rank Program error"),
                'body': _.str.sprintf(_t("Card rank program '%s' not found."), current_rank[1]),
            });
        } else {
            order.card_rank_program = card_rank_program;
            order.card_rank_applied = true;
            for (let line of order.orderlines) {
                line.action_apply_card_rank(card_rank_program);
            }
        }
    }
}

CardButton.template = 'CardButton';

ProductScreen.addControlButton({
    component: CardButton, position: ['after', 'RefundButton'], condition: function () {
        return this.partner && this.partner.card_rank_by_brand[this.env.pos.pos_branch[0].id] && this.env.pos.get_order().orderlines.length > 0 && !this.env.pos.get_order().card_rank_applied;
    }
});

Registries.Component.add(CardButton);
