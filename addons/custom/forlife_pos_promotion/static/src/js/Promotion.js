/** @odoo-module **/

import { Order, Orderline, PosGlobalState} from 'point_of_sale.models';
import Registries from 'point_of_sale.Registries';
import session from 'web.session';
import concurrency from 'web.concurrency';
import { Gui } from 'point_of_sale.Gui';
import { round_decimals,round_precision } from 'web.utils';
import core from 'web.core';

export class PromotionUsageLine {
    /**
     * @param {number} id of promotion.program
     * @param {number} id id of promotion.code
     * @param {number} original_price: price before discount
     * @param {number} discount_amount: discount amount
     */
    constructor(program_id, code_id=null, original_price, discount_amount) {
        this.program_id = program_id;
        this.code_id = code_id;
        this.original_price = original_price;
        this.discount_amount = discount_amount;
    }
}

const PosPromotionGlobalState = (PosGlobalState) => class PosPromotionGlobalState extends PosGlobalState {
    //@override
    async _processData(loadedData) {
        this.couponCache = {};
        await super._processData(loadedData);
        this.promotionPrograms = loadedData['promotion.program'] || [];
        this.promotionComboLines = loadedData['promotion.combo.line'] || [];
        this.rewardLines = loadedData['promotion.reward.line'] || [];
        this.monthData = loadedData['month.data'] || [];
        this.dayofmonthData = loadedData['dayofmonth.data'] || [];
        this.dayofweekData = loadedData['dayofweek.data'] || [];
        this._loadPromotionData();
    }
    _loadPromotionData() {
        this.promotion_program_by_id = {};
        this.reward_line_by_id = {};
        var self = this;
        for (const program of this.promotionPrograms) {
            this.promotion_program_by_id[program.id] = program;

            var months = program.month_ids.reduce(function (accumulator, m) {
                var monthName = self.monthData.find((elem) => elem.id === m);
                accumulator.add(monthName.code);
                return accumulator
            }, new Set());
            program.applied_months = months;

            var days = program.dayofmonth_ids.reduce(function (accumulator, d) {
                var day = self.dayofmonthData.find((elem) => elem.id === d);
                accumulator.add(day.code);
                return accumulator
            }, new Set());
            program.applied_days = days;

            program.comboFormula = [];
            program.rewards = [];
        };
        for (const item of this.promotionComboLines) {
            item.valid_product_ids = new Set(item.valid_product_ids);
            item.program_id = this.promotion_program_by_id[item.program_id[0]];
            item.program_id.comboFormula.push(item);
        };
        for (const reward of this.rewardLines) {
            this.reward_line_by_id[reward.id] = reward;
            reward.program_id = this.promotion_program_by_id[reward.program_id[0]];
            reward.program_id.rewards.push(reward);
        };
    }
}

Registries.Model.extend(PosGlobalState, PosPromotionGlobalState)

const PosPromotionOrderline = (Orderline) => class PosPromotionOrderline extends Orderline {
    export_as_JSON() {
        const result = super.export_as_JSON(...arguments);
        result.promotion_usage_ids = [];
        result.applied_promotion_ids = [];
        result.original_price = this.get_unit_price();
        return result;
    }
    init_from_JSON(json) {
        this.promotion_usage_ids = json.promotion_usage_ids;
        this.applied_promotion_ids = json.applied_promotion_ids;
        this.original_price = json.original_price;
        super.init_from_JSON(...arguments);
    }
    set_quantity(quantity, keep_price) {
        return super.set_quantity(...arguments);
    }
}
Registries.Model.extend(Orderline, PosPromotionOrderline);


const PosPromotionOrder = (Order) => class PosPromotionOrder extends Order {
    constructor() {
        super(...arguments);
        this._initializePrograms({});
//        this.invalidCoupons = true;
    }
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
//        json.disabledRewards = [...this.disabledRewards];
//        json.codeActivatedProgramRules = this.codeActivatedProgramRules;
//        json.codeActivatedCoupons = this.codeActivatedCoupons;
//        json.couponPointChanges = this.couponPointChanges;
        return json;
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
    }
    /**
     * @override
     */
    set_partner(partner) {
        const oldPartner = this.get_partner();
        super.set_partner(partner);
    }

    _programIsApplicableAutomatically(program) {
        if (!program.with_code && program.promotion_type == 'combo') {
            return true;
        }
        return false;
    }

    async _initializePrograms(v) {
        this.copy_order = this;
        this.copy_order_lines = this;
    }
    /*
    * recursion function
    * return {number} count of  combo
    */
    _checkNumberOfCombo(comboProgram, order_lines, count) {
        count = count || 0;
        var comboFormula = comboProgram.comboFormula;
        var enoughCombo = true;
        for (const part of comboFormula) {
            var order_lines_has_valid_product = order_lines.filter(l => part.valid_product_ids.has(l.product.id));
            var qty_total = order_lines_has_valid_product.reduce((accumulator, l) => accumulator + l.quantity, 0);
            if (qty_total < part.quantity) {enoughCombo = false; break;};
        };
        if (enoughCombo == false) {
            return count;
        } else {
            for (const part of comboFormula) {
                var qty_to_take_on_candidates = part.quantity
                for (const ol of order_lines.filter(ol => part.valid_product_ids.has(ol.product.id))) {
                    var qty_taken_on_candidate = Math.min(qty_to_take_on_candidates, part.quantity);
                    ol.quantity = ol.quantity - qty_taken_on_candidate;
                    qty_to_take_on_candidates -= qty_taken_on_candidate;
                    if (qty_to_take_on_candidates <= 0.0) {break;};
                };
            };
            return this._checkNumberOfCombo(comboProgram, order_lines, count + 1);
        }
    }

    verifyComboProgramOnOrder(toVerifyPromotionPrograms) {
        var comboProgramToCheck = new Set();
        var comboProgramIsVerified = new Object();
        for (const program of toVerifyPromotionPrograms) {
            if (this._programIsApplicableAutomatically(program)) {
                comboProgramToCheck.add(program);
            };
        };
        for (const program of comboProgramToCheck) {
            var to_check_order_lines = this._get_regular_order_lines().map(obj => ({...obj}));
            var NumberOfCombo = this._checkNumberOfCombo(program, to_check_order_lines, 0);
            if (NumberOfCombo >= 1) {
                comboProgramIsVerified[program.id] = NumberOfCombo;
            };
        };
        return comboProgramIsVerified;
    }

}
Registries.Model.extend(Order, PosPromotionOrder);