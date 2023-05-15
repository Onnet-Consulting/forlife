/** @odoo-module **/

import {Order, Orderline} from 'point_of_sale.models';
import Registries from 'point_of_sale.Registries';

var utils = require('web.utils');
var round_pr = utils.round_precision;

const PosOrderCardRank = (Order) => class extends Order {
    constructor(obj, options) {
        super(...arguments);
        if (!this.card_rank_program) {
            this.card_rank_program = null;
            this.order_status_format = this.order_status_format || false;
            this.order_status_tokyolife = this.order_status_tokyolife || false;
        }
    }

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.card_rank_program = json.card_rank_program || null;
        this.order_status_format = json.order_status_format || false;
        this.order_status_tokyolife = json.order_status_tokyolife || false;
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_rank_program = this.card_rank_program;
        json.order_status_format = this.order_status_format;
        json.order_status_tokyolife = this.order_status_tokyolife;
        return json;
    }

    set_partner(partner) {
        const oldPartner = this.get_partner();
        super.set_partner(partner);
        if (partner) {
            this.order_status_format = partner.card_rank_status_format;
            this.order_status_tokyolife = partner.card_rank_status_tokyolife;
        }
        let newPartner = this.get_partner();
        if (oldPartner !== newPartner && this.card_rank_program) {
            this.action_reset_card_rank_program();
        }
    }

    add_product(product, options) {
        super.add_product(...arguments);
        this.action_reset_card_rank_program();
    }

    get_total_without_tax() {
        return super.get_total_without_tax() - this.get_total_card_rank_discount();
    }

    get_total_card_rank_discount() {
        return round_pr(this.orderlines.reduce((function (sum, orderLine) {
            return sum + orderLine.get_card_rank_discount();
        }), 0), this.pos.currency.rounding);
    }

    action_apply_card_rank_program(card_rank_program, order_line_data) {
        this.card_rank_program = card_rank_program;
        for (let line of this.orderlines) {
            line.action_apply_card_rank(order_line_data.find(data => data.id === line.id));
        }
    }

    action_reset_card_rank_program() {
        if (this.card_rank_program) {
            this.card_rank_program = null;
            this._resetPromotionPrograms();
            for (let line of this.orderlines) {
                line.action_reset_card_rank();
            }
        }
    }

    order_can_apply_card_rank() {
        let res = false;
        let partner = this.get_partner();
        if (partner) {
            let card_rank = partner.card_rank_by_brand[this.pos.pos_branch[0].id];
            if (card_rank) {
                let cr_program = this.pos.card_rank_program_by_rank_id[card_rank[0]] || {};
                let customer_not_apply = cr_program.customer_not_apply || [];
                if ((customer_not_apply.length === 0) || (cr_program && customer_not_apply.length > 0 && !customer_not_apply.includes(partner.id))) {
                    res = true;
                }
            }
        }
        return res;
    }


};
Registries.Model.extend(Order, PosOrderCardRank);
const PosOrderLineCardRank = (Orderline) => class extends Orderline {
    constructor(obj, options) {
        super(...arguments);
        if (!this.card_rank_discount) {
            this.card_rank_discount = 0;
        }
        if (!this.card_rank_applied) {
            this.card_rank_applied = false;
        }
        if (!this.old_point) {
            this.old_point = null;
        }
    }

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.card_rank_discount = json.card_rank_discount || 0;
        this.card_rank_applied = json.card_rank_applied || false;
        this.old_point = json.old_point || null;
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_rank_discount = this.card_rank_discount;
        json.card_rank_applied = this.card_rank_applied;
        json.old_point = this.old_point;
        return json;
    }

    set_quantity(quantity, keep_price) {
        let oldQty = this.quantity;
        let result = super.set_quantity(...arguments);
        if (oldQty !== this.quantity) {
            this.order.action_reset_card_rank_program();
        }
        return result;
    }

    set_discount(discount) {
        let oldDiscount = this.get_discount();
        let result = super.set_discount(...arguments);
        if (oldDiscount !== this.discount) {
            this.order.action_reset_card_rank_program();
        }
        return result;
    }

    action_apply_card_rank(line_data) {
        if (line_data && line_data.card_rank_disc > (line_data.total_discounted + line_data.extra_card_rank_disc)) {
            this.card_rank_discount = line_data.card_rank_disc;
            this.card_rank_applied = true;
            this.old_point = this.point;
            this.set_point(null);
            this.reset_unit_price();
            this.promotion_usage_ids = [];

        } else if (line_data && line_data.extra_card_rank_disc > 0) {
            this.card_rank_discount = line_data.extra_card_rank_disc;
            this.card_rank_applied = true;
            this.old_point = this.point;
        }
    }

    action_reset_card_rank() {
        if (this.card_rank_applied) {
            this.card_rank_discount = 0;
            this.card_rank_applied = false;
            this.set_point(this.old_point);
        }
    }

    get_card_rank_discount() {
        return this.card_rank_discount || 0;
    }
    get_display_price_after_discount() {
        var total = super.get_display_price_after_discount(...arguments);
        return total - this.get_card_rank_discount();
    }

    get_discount_detail(cr_program) {
        let total_discounted = (this.get_total_discounted() || 0) - (this.get_point() || 0);
        let original_price = this.get_original_price();
        let card_rank_disc = 0;
        let extra_card_rank_disc = 0;
        let check_skip_cr = false;
        if (this.promotion_usage_ids.length > 0) {
            for (let promotion of this.promotion_usage_ids) {
                if (this.pos.promotion_program_by_id[promotion.program_id].skip_card_rank === true) {
                    check_skip_cr = true;
                    break;
                }
            }
        }
        if (check_skip_cr === false) {
            let quantity = this.get_quantity();
            card_rank_disc = cr_program.on_original_price * (quantity * original_price) / 100;
            let promotion_pricelist = this.pos.promotionPricelistItems.find(p => p.product_id === this.product.id);
            if (promotion_pricelist && promotion_pricelist.valid_customer_ids.has(this.order.get_partner().id) && this.promotion_usage_ids.find(p => p.program_id === promotion_pricelist.program_id)) {
                let pricelist_disc = (1 - (promotion_pricelist.fixed_price / original_price)) * 100;
                for (let line of cr_program.extra_discount) {
                    if (pricelist_disc > line.from && pricelist_disc <= line.to) {
                        extra_card_rank_disc = line.disc * quantity * promotion_pricelist.fixed_price / 100;
                        break;
                    }
                }
            }
        }
        return {
            id: this.id,
            product_name: this.product.display_name,
            price: original_price,
            total_discounted: total_discounted,
            card_rank_disc: card_rank_disc,
            extra_card_rank_disc: extra_card_rank_disc,
            apply_cr_discount: card_rank_disc - (total_discounted + extra_card_rank_disc) > 0,
        }
    }
};
Registries.Model.extend(Orderline, PosOrderLineCardRank);