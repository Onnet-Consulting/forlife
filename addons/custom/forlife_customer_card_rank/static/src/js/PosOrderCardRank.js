/** @odoo-module **/

import {Order, Orderline} from 'point_of_sale.models';
import Registries from 'point_of_sale.Registries';

const PosOrderCardRank = (Order) => class extends Order {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.card_rank_program = json.card_rank_program || null;
        this.card_rank_applied = json.card_rank_applied || false;
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_rank_program = this.card_rank_program;
        json.card_rank_applied = this.card_rank_applied;
        return json;
    }
};
Registries.Model.extend(Order, PosOrderCardRank);
const PosOrderLineCardRank = (Orderline) => class extends Orderline {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.discount_card_rank = json.discount_card_rank || 0;
        this.order_line_card_rank_applied = json.order_line_card_rank_applied || false;
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.discount_card_rank = this.discount_card_rank;
        json.order_line_card_rank_applied = this.order_line_card_rank_applied;
        return json;
    }

    action_apply_card_rank(cr_program) {
        for (let line of cr_program.discounts) {
            if (this.discount > line[1][0] && this.discount <= line[1][1]) {
                this.discount_card_rank = line[0]
                break;
            }
        }
        this.order_line_card_rank_applied = true;
    }

    action_reset_card_rank() {
        this.discount_card_rank = 0;
        this.order_line_card_rank_applied = false;
    }
};
Registries.Model.extend(Orderline, PosOrderLineCardRank);