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
            const order_lines = order.get_orderlines()
            let order_line_data = [];
            for (let line of order_lines) {
                order_line_data.push(line.get_discount_detail(card_rank_program));
            }
            const {confirmed, payload: res} = await this.showPopup('ShowDiscountDetailPopup', {
                order_lines: order_line_data,
            });
            if (confirmed) {
                order.action_apply_card_rank_program(card_rank_program.id, order_line_data);
            }
        }
    }
}

CardButton.template = 'CardButton';

ProductScreen.addControlButton({
    component: CardButton,
    position: ['after', 'RefundButton'],
    condition: function () {
        let order = this.env.pos && this.env.pos.get_order();
        return order.orderlines.length > 0 && !order.card_rank_program && order.order_can_apply_card_rank();
    }
});

Registries.Component.add(CardButton);
