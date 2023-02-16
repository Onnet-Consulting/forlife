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
    constructor(program_id, code_id=null, original_price, new_price, discount_amount) {
        this.program_id = program_id;
        this.code_id = code_id;
        this.original_price = original_price;
        this.new_price = new_price;
        this.discount_amount = discount_amount;
    }
}

export class PosPromotionCode {
    /**
     * @param {string} code coupon code
     * @param {number} id id of loyalty.card, negative if it is cache local only
     * @param {number} program_id id of loyalty.program
     * @param {number} partner_id id of res.partner
     * @param {number} balance points on the coupon, not counting the order's changes
     */
    constructor(code, id, program_id, partner_id, balance) {
        this.code = code;
        this.id = id || nextId--;
        this.program_id = program_id;
        this.partner_id = partner_id;
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
        this.hourData = loadedData['hour.data'] || [];
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

            var hours = program.hour_ids.reduce(function (accumulator, h) {
                var hour = self.hourData.find((elem) => elem.id === h);
                accumulator.add(hour.code);
                return accumulator
            }, new Set());
            program.applied_hours = hours;

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

    async load_server_data() {
        await super.load_server_data(...arguments);
        if (this.selectedOrder) {
            this.selectedOrder._updateActivatedPromotionPrograms();
        };
    }

    set_order(order) {
        const result = super.set_order(...arguments);
        if (order) {
            order._updateActivatedPromotionPrograms();
        };
        return result;
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
        this._initializePromotionPrograms({});
    }
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.activatedComboPrograms = this.activatedComboPrograms;
        json.activatedCodePrograms = this.activatedCodePrograms;
        json.activatedInputCodes = this.activatedInputCodes;
        return json;
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.activatedComboPrograms = new Set(json.activatedComboPrograms);
        this.activatedCodePrograms = new Set(json.activatedCodePrograms);
        this.activatedInputCodes = json.activatedInputCodes;
    }
    /**
     * @override
     */
    set_partner(partner) {
        const oldPartner = this.get_partner();
        super.set_partner(partner);
        if (oldPartner !== this.get_partner()) {
            this._updateActivatedPromotionPrograms();
        };
    }

    _programIsApplicableAutomatically(program) {

        if (!program.promotion_type == 'combo') {return false;};
        if (program.with_code) {
            if (!this.activatedInputCodes.map(code => code.program_id).includes(program.id)) {return false;};
        };
        var day = this.creation_date.getDay();
        var date = this.creation_date.getDate();
        var month = this.creation_date.getMonth();
        var hour = this.creation_date.getHours();
        var hasDate = program.applied_days.has(this.creation_date.getDate());
        var hasMonth = program.applied_months.has(this.creation_date.getMonth() + 1);
        var hasHour = program.applied_hours.has(this.creation_date.getHours());
        if (!hasDate || !hasMonth || !hasHour) {return false};
        return true;
    }

    add_product(product, options) {
        super.add_product(...arguments);
        this._updateActivatedPromotionPrograms();
    }

    async _initializePromotionPrograms(v) {
        this.copy_order = this;
        this.copy_order_lines = this;

        if (!this.activatedCodePrograms) {
            this.activatedCodePrograms = new Set();
        };
        if (!this.activatedComboPrograms) {
            this.activatedComboPrograms = new Set();
        };
        if (!this.activatedInputCodes) {
            this.activatedInputCodes = [];
        };
    }

    async _updateActivatedPromotionPrograms() {
        let activatedCodes = this.activatedInputCodes;
        if (Array.isArray(this.activatedInputCodes)) {
            for (let code of activatedCodes) {
                let program = this.pos.promotion_program_by_id[code.program_id];
                if (program && program.promotion_type == 'combo') {
                    this.activatedComboPrograms.add(code.program_id);
                }
                else if (program && program.promotion_type == 'code') {
                    this.activatedCodePrograms.add(code.program_id);
                };
            };
            for (let proID of Object.keys(this.verifyComboProgramOnOrder(this.pos.promotionPrograms))) {
                this.activatedComboPrograms.add(parseInt(proID));
            };
        };
    }
    /*
    * recursion function
    * return {number} count of  combo
    */
    _checkNumberOfCombo(comboProgram, order_lines, to_discount_line_vals , count) {
        count = count || 0;
        to_discount_line_vals = to_discount_line_vals || [];
        var comboFormula = comboProgram.comboFormula;
        var enoughCombo = true;
        for (const part of comboFormula) {
            var order_lines_has_valid_product = order_lines.filter(l => part.valid_product_ids.has(l.product.id));
            var qty_total = order_lines_has_valid_product.reduce((accumulator, l) => accumulator + l.quantity, 0);
            if (qty_total < part.quantity) {enoughCombo = false; break;};
        };
        if (enoughCombo == false) {
            return [order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count];
        } else {
            var oneCombo = []
            for (const part of comboFormula) {
                var qty_to_take_on_candidates = part.quantity
                for (const ol of order_lines.filter(ol => part.valid_product_ids.has(ol.product.id)  && ol.quantity > 0)) {
                    var qty_taken_on_candidate = Math.min(qty_to_take_on_candidates, ol.quantity);
                    /* ============ */
                    ol.quantity = ol.quantity - qty_taken_on_candidate;
                    oneCombo.push({
                        product: ol.product,
                        quantity: qty_taken_on_candidate,
                        price: ol.product.lst_price,
                    });
                    qty_to_take_on_candidates -= qty_taken_on_candidate;
                    if (qty_to_take_on_candidates <= 0.0) {break;};
                };
            };
            to_discount_line_vals.push(oneCombo);
            return this._checkNumberOfCombo(comboProgram, order_lines, to_discount_line_vals, count + 1);
        }
    }

    /* return {<program_id>: number_of_combo}*/
    verifyComboProgramOnOrder(toVerifyPromotionPrograms) {
        var comboProgramToCheck = new Set();
        var comboProgramIsVerified = new Object();
        for (const program of toVerifyPromotionPrograms) {
            if (this._programIsApplicableAutomatically(program)) {
                comboProgramToCheck.add(program);
            };
        };
        console.log('comboProgramToCheck', comboProgramToCheck)
        for (const program of comboProgramToCheck) {
            var to_check_order_lines = this._get_regular_order_lines().map(obj => ({...obj}));
            let NumberOfCombo = this._checkNumberOfCombo(program, to_check_order_lines, [] , 0)[2];
            if (NumberOfCombo >= 1) {
                comboProgramIsVerified[program.id] = NumberOfCombo;
            };
        };
        console.log('comboProgramIsVerified', comboProgramIsVerified)
        return comboProgramIsVerified;
    }

    getPotentialPrograms() {
        var numberOfProgramsValues = this.verifyComboProgramOnOrder(this.pos.promotionPrograms);
        return Object.entries(numberOfProgramsValues)
                    .reduce((tmp, p) => { console.log(p); tmp.push({
                        program : this.pos.promotionPrograms.find((pro)=> pro.id == p[0]),
                        number: p[1],
                        id: p[0] }); return tmp;
                    }, []);
    }

    testFunction() {
        let promotionProgramsList = this.getPotentialPrograms().map((pro) => pro['program']);
        console.log('================= testFunction')
        let order_lines = this._get_regular_order_lines().map(obj => ({...obj}));
        this.computeForListOfCombo(order_lines, promotionProgramsList);
    }

    computeNewPriceForComboProgram(disc_total, base_total, prePrice, quantity) {
        let subTotalLine = prePrice * quantity;
        let discAmount = base_total > 0.0 ? subTotalLine / base_total * disc_total : 0.0;
        let newPrice = (subTotalLine - discAmount) / quantity;
        return [newPrice, discAmount]
    }

    applyAProgramToLineVales(program, comboLineList) {
        // Combo: Mua Combo, giảm tiền
        if (program.reward_type == 'combo_amount' && program.promotion_type == 'combo') {
            let disc_total_amount = program.disc_amount;
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            for (let comboLine of comboLineList) {
                let originalPrice = comboLine.price;
                let [newPrice, discAmountInLine] = this.computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                comboLine.price = newPrice;
                comboLine['promotion_usage_ids'] = [];
                comboLine.promotion_usage_ids.push(new PromotionUsageLine(program, null, originalPrice, newPrice, discAmountInLine));
            }
        }
        // Mua combo giảm phần trăm
        else if (program.reward_type == 'combo_percent' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = base_total_amount * program.disc_percent / 100;
            if (program.disc_max_amount) {
                disc_total_amount = disc_total_amount < program.disc_max_amount ? disc_total_amount : program.disc_max_amount;
            }
            for (let comboLine of comboLineList) {
                let originalPrice = comboLine.price;
                let [newPrice, discAmountInLine] = this.computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                comboLine.price = newPrice;
                comboLine['promotion_usage_ids'] = [];
                comboLine.promotion_usage_ids.push(new PromotionUsageLine(program, null, originalPrice, newPrice, discAmountInLine));
            }
        }
        // Mua 1 combo với giá cố định
        else if (program.reward_type == 'combo_fixed_price' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = base_total_amount - program.disc_fixed_price
            disc_total_amount = disc_total_amount > 0 ? disc_total_amount : 0;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmountInLine] = this.computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine['promotion_usage_ids'] = [];
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program, null, originalPrice, newPrice, discAmountInLine));
                }
            }
        }
        return comboLineList;
    }

    computeForListOfCombo(orderLines, listOfComboProgram) {
        let lines_to_check = orderLines;
        let to_apply_lines = {};
        for (const program of listOfComboProgram) {
            var [remainingOrderLines, to_discount_line_vals, numberOfCombo] = this._checkNumberOfCombo(program, orderLines, [], 0);
            lines_to_check = remainingOrderLines;
            // ---------------------------------------------------------------- //
            for (let i = 0; i < to_discount_line_vals.length; i++) {
                let result = this.applyAProgramToLineVales(program, to_discount_line_vals[i]);
                if (to_apply_lines.hasOwnProperty(program.id)) {
                    to_apply_lines[program.id].push(...result);
                }
                else {
                    to_apply_lines[program.id] = result;
                };
            };
        };
        return [to_apply_lines, orderLines];
    }

    async _activatePromotionCode(code) {

        if (!this.pos.promotionPrograms.some(p => p.promotion_type == 'code' || p.with_code == true)) {
            return 'Not found an available Promotion Program needed Code to be activated';
        };

        if (this.activatedInputCodes.find((c) => c.code === code)) {
            return 'That coupon code has already been scanned and activated.';
        };

        const customer = this.get_partner();
        const { successful, payload } = await this.pos.env.services.rpc({
            model: 'pos.config',
            method: 'use_promotion_code',
            args: [
                [this.pos.config.id],
                code,
                this.creation_date,
                customer ? customer.id : false,
            ],
            kwargs: { context: session.user_context },
        });
        if (successful) {
            const codeObj = new PosPromotionCode(code, payload.code_id, payload.program_id, payload.coupon_partner_id);
            this.activatedInputCodes.push(codeObj);
            await this._updateActivatedPromotionPrograms();
        } else {
            return payload.error_message;
        };
        return true;
    }

    async activatePromotionCode(code) {
        const res = await this._activatePromotionCode(code);
        if (res !== true) {
            Gui.showNotification(res);
        } else {
            Gui.showNotification(_.str.sprintf('Successfully activate a promotion code.'),3000);
        };
    }

}
Registries.Model.extend(Order, PosPromotionOrder);
//
//function getAllCombinations(inputArray) {
//  var resultArray = [];
//  var combine = function() {
//    for (var i in inputArray) {
//      var temp = [];
//      var tempResult = [];
//      for (var j in arguments) {
//        tempResult.push(inputArray[arguments[j]]);
//        if (arguments[j] == i) {
//          temp = false;
//        } else if (temp) {
//          temp.push(arguments[j]);
//        }
//      }
//      if (temp) {
//        temp.push(i);
//        combine.apply(null, temp);
//      }
//    }
//    if (tempResult.length == inputArray.length) {
//      resultArray.push(tempResult);
//    }
//    return resultArray;
//  };
//  return combine();
//}