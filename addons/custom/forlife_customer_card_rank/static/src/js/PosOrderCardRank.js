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
        }
    }

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.card_rank_program = json.card_rank_program || null;
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_rank_program = this.card_rank_program;
        return json;
    }

    set_partner(partner) {
        const oldPartner = this.get_partner();
        super.set_partner(partner);
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
            for (let line of this.orderlines) {
                line.action_reset_card_rank();
            }
        }
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
        if (!this.old_promotion_usage_ids) {
            this.old_promotion_usage_ids = null;
        }
    }

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.card_rank_discount = json.card_rank_discount || 0;
        this.card_rank_applied = json.card_rank_applied || false;
        this.old_point = json.old_point || null;
        this.old_promotion_usage_ids = json.old_promotion_usage_ids || [];
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_rank_discount = this.card_rank_discount;
        json.card_rank_applied = this.card_rank_applied;
        json.old_point = this.old_point;
        json.old_promotion_usage_ids = this.old_promotion_usage_ids;
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
        if (line_data && line_data.total_discounted < line_data.card_rank_disc) {
            this.card_rank_discount = line_data.card_rank_disc;
            this.card_rank_applied = true;
            this.old_point = this.point;
            this.old_promotion_usage_ids = this.promotion_usage_ids;
            this.set_point(null);
            this.promotion_usage_ids = [];

        }
    }

    action_reset_card_rank() {
        if (this.card_rank_applied) {
            this.card_rank_discount = 0;
            this.card_rank_applied = false;
            this.set_point(this.old_point);
            this.promotion_usage_ids = this.old_promotion_usage_ids;
        }
    }

    get_card_rank_discount() {
        return this.card_rank_discount || 0;
    }

    get_discount_detail(cr_program) {
        let total_discounted = (this.get_total_discounted() || 0) - (this.get_point() || 0);
        let card_rank_disc = cr_program.on_original_price * (this.get_quantity() * this.get_unit_price()) / 100;
        let promotion_pricelist = this.pos.promotionPricelistItems.find(p => p.product_id === this.product.id);
        if (promotion_pricelist && promotion_pricelist.valid_customer_ids.has(this.order.get_partner().id)) {
            let pricelist_disc = 1 - (promotion_pricelist.fixed_price / this.get_unit_price());
            for (let line of cr_program.extra_discount) {
                if (pricelist_disc > line.from && pricelist_disc <= line.to) {
                    card_rank_disc = card_rank_disc + (line.disc * (this.get_quantity() * this.get_unit_price() - card_rank_disc) / 100);
                    break;
                }
            }
        }
        return {
            id: this.id,
            product_name: this.product.display_name,
            price: this.price,
            total_discounted: total_discounted,
            card_rank_disc: card_rank_disc,
            apply_cr_discount: card_rank_disc - total_discounted > 0,
        }
    }
};
Registries.Model.extend(Orderline, PosOrderLineCardRank);