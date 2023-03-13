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
        if (oldPartner && newPartner && (oldPartner !== newPartner) && this.card_rank_program) {
            if (!newPartner.card_rank_by_brand || (newPartner.card_rank_by_brand && (newPartner.card_rank_by_brand[this.pos.pos_branch[0].id] !== this.card_rank_program.card_rank_id))) {
                this.action_reset_card_rank_program();
            }
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

    action_apply_card_rank_program(card_rank_program) {
        this.card_rank_program = card_rank_program;
        for (let line of this.orderlines) {
            line.action_apply_card_rank(card_rank_program);
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

    check_all_orderline_reseted() {
        const notApplied = this.get_orderlines().find(line => line.card_rank_applied);
        if (!notApplied && this.card_rank_program) {
            this.card_rank_program = null;
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
    }

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.card_rank_discount = json.card_rank_discount || 0;
        this.card_rank_applied = json.card_rank_applied || false;
    }

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.card_rank_discount = this.card_rank_discount;
        json.card_rank_applied = this.card_rank_applied;
        return json;
    }

    set_quantity(quantity, keep_price) {
        let oldQty = this.quantity;
        let result = super.set_quantity(...arguments);
        if (oldQty !== this.quantity) {
            this.action_reset_card_rank();
            this.order.check_all_orderline_reseted();
        }
        return result;
    }

    set_discount(discount) {
        let oldDiscount = this.get_discount();
        let result = super.set_discount(...arguments);
        if (oldDiscount !== this.discount) {
            this.action_reset_card_rank();
            this.order.check_all_orderline_reseted();
        }
        return result;
    }

    set_point(point) {
        let oldPoint = this.get_point();
        let result = super.set_point(...arguments);
        if (oldPoint !== this.point) {
            this.action_reset_card_rank();
            this.order.check_all_orderline_reseted();
        }
        return result;
    }

    action_apply_card_rank(cr_program) {
        var total_percent_discounted = this.discount + ((this.get_total_discounted() - this.get_point()) / (this.get_quantity() * this.get_unit_price()) * 100);
        for (let line of cr_program.discounts) {
            if (total_percent_discounted > line.from && total_percent_discounted <= line.to) {
                this.card_rank_discount = line.disc;
                break;
            }
        }
        this.card_rank_applied = true;
    }

    action_reset_card_rank() {
        if (this.card_rank_applied) {
            this.card_rank_discount = 0;
            this.card_rank_applied = false;
        }
    }

    get_card_rank_discount() {
        return (this.get_quantity() * this.get_unit_price() * this.card_rank_discount / 100) || 0;
    }
};
Registries.Model.extend(Orderline, PosOrderLineCardRank);