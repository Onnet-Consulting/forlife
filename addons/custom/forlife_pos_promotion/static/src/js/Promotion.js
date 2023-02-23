/** @odoo-module **/
//odoo.define('forlife_pos_promotion.modelsPromotion ', function (require) {
//    "use strict";

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
            program.valid_product_ids = new Set(program.valid_product_ids);
            program.valid_customer_ids = new Set(program.valid_customer_ids);
            program.discount_product_ids = new Set(program.discount_product_ids);
            program.reward_product_ids = new Set(program.reward_product_ids);

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

    constructor() {
        super(...arguments);
        this.promotion_usage_ids = this.promotion_usage_ids || [];
    }

    export_as_JSON() {

        const result = super.export_as_JSON(...arguments);

        result.original_price = this.get_lst_price();

        let promotion_usage_ids = [];
        this.promotion_usage_ids.forEach(_.bind( function(item) {
            return promotion_usage_ids.push([0, 0, item]);
        }, this));
        result.promotion_usage_ids = promotion_usage_ids;

        return result;
    }
    init_from_JSON(json) {
        this.original_price = json.original_price;
        this.promotion_usage_ids = [];
        var promotion_usage_ids = json.promotion_usage_ids || [];
        if (promotion_usage_ids.length > 0) {
            for (var i = 0; i < promotion_usage_ids.length; i++) {
                var item = promotion_usage_ids[i][2];
                this.promotion_usage_ids.push(new PromotionUsageLine(
                    item.program_id,
                    item.code_id,
                    item.original_price,
                    item.new_price,
                    item.discount_amount
                ));
            }
        }
        super.init_from_JSON(...arguments);
    }

    set_quantity(quantity, keep_price) {
        let result = super.set_quantity(...arguments);
        this.order._updateActivatedPromotionPrograms();
        if (this.promotion_usage_ids !== undefined && this.promotion_usage_ids.length > 0) {
            this.promotion_usage_ids = [];
            this.reset_unit_price();
            this.order._resetPromotionPrograms(false);
        };
        return result;
    }

    get_original_price() {
        return this.product.get_display_price(this.order.pricelist, 1)
    }

    get_total_discounted() {
        if (!this.promotion_usage_ids) {
            return 0.0
        }
        let result = this.promotion_usage_ids.reduce((accum, usage) => {return accum + usage.discount_amount;}, 0.0)
        return result || 0.0;
    }

    _isDiscountedComboProgram() {
        return this.promotion_usage_ids.some(pro => pro.discount_amount > 0.0)
    }

    reset_unit_price() {
        this.set_unit_price(this.product.get_price(this.order.pricelist, this.get_quantity()));
    }

    is_applied_promotion() {
        let result = true;
        if (!this.promotion_usage_ids) {
            result = false;
        } else if (!this.promotion_usage_ids.length > 0) {
            result = false;
        }
        return result;

    }

    get_applied_promotion_str() {
        let result = [];
        if (!this.promotion_usage_ids) {
            return []
        };
        for (const promotion of this.promotion_usage_ids) {
            result.push({id: promotion.program_id, str: this.pos.promotion_program_by_id[promotion.program_id].name});
        };
        return result;
    }
};
Registries.Model.extend(Orderline, PosPromotionOrderline);


const PosPromotionOrder = (Order) => class PosPromotionOrder extends Order {
    constructor() {
        super(...arguments);
        this._initializePromotionPrograms({});
    }
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        let activatedCombo = new Set(this.activatedComboPrograms);
        let activatedCode = new Set(this.activatedCodePrograms);
        json.activatedComboPrograms = [...activatedCombo];
        json.activatedCodePrograms = [...activatedCode];
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
            this.activatedInputCodes = [];
            this._updateActivatedPromotionPrograms();
        };
    }

    _programIsApplicableAutomatically(program) {

        if (!program.promotion_type == 'combo') {return false;};
        if (program.with_code) {
            if (this.activatedInputCodes) {
                if (!this.activatedInputCodes.map(code => code.program_id).includes(program.id)) {return false;};
            } else {return false;};
        };
        const customer = this.partner;
        if (!program.valid_customer_ids.has(customer ? customer.id : 0)) {return false;};

        var hasDate = program.applied_days.has(this.creation_date.getDate()) || program.applied_days.size == 0;
        var hasMonth = program.applied_months.has(this.creation_date.getMonth() + 1) || program.applied_months.size == 0;
        var hasHour = program.applied_hours.has(this.creation_date.getHours()) || program.applied_hours.size == 0;
        if (!hasDate || !hasMonth || !hasHour) {;return false};
        return true;
    }

    add_product(product, options) {
        super.add_product(...arguments);
        this._updateActivatedPromotionPrograms();
    }

    set_orderline_options(line, options) {
        super.set_orderline_options(...arguments);
        if (options && options.is_reward_line) {
            line.price_manually_set = true;
        }
        line.promotion_usage_ids = options.promotion_usage_ids || [];
        line.giftBarcode = options.giftBarcode;
        line.giftCardId = options.giftCardId;
        line.eWalletGiftCardProgram = options.eWalletGiftCardProgram;
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

    _resetPromotionPrograms(resetActivatedPrograms=true) {
        if (resetActivatedPrograms) {
            this.activatedInputCodes = [];
            this.activatedComboPrograms = new Set();
            this.activatedCodePrograms = new Set();
        }
        this.orderlines.remove(this._get_reward_lines()); // TODO: Xác định reward line của CTKM nào
        let orderlines = this.orderlines.filter(line => line._isDiscountedComboProgram())
        orderlines.forEach(line => line.reset_unit_price());
        orderlines.forEach(line => line.promotion_usage_ids = []);

        this._updateActivatedPromotionPrograms();
    }

    async _updateActivatedPromotionPrograms() {
        this.activatedComboPrograms = new Set();
        this.activatedCodePrograms = new Set();
        let validPromotionPrograms = this.verifyComboProgramOnOrder(this.pos.promotionPrograms);
        for (let proID of Object.keys(validPromotionPrograms)) {
            if (this.pos.promotion_program_by_id[proID].promotion_type === 'combo') {
                this.activatedComboPrograms.add(parseInt(proID));
            } else if (this.pos.promotion_program_by_id[proID].promotion_type === 'code') {
                this.activatedCodePrograms.add(parseInt(proID));
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

    // get reward lines
    _get_reward_lines() {
        const orderLines = super.get_orderlines(...arguments);
        if (orderLines) {
            return orderLines.filter((line) => line.is_reward_line);
        }
        return orderLines;
    }

    // get copy of line
    _get_clone_order_lines(remainingLines) {
        let lines = [];
        remainingLines.forEach((l) => {
            lines.push({
                product: {
                    id: l.product.id,
                    lst_price: l.product.lst_price,
                },
                quantity: l.quantity,
                promotion_usage_ids: [...(l.promotion_usage_ids || [])],
                employee_id: l.employee_id,
                id: l.id,
                price: l.price,
                full_product_name: l.full_product_name,
                tax_ids: l.tax_ids
            });
        })
        return JSON.parse(JSON.stringify(lines));
    }

    _get_program_usage_ids() {
        let lines = this.get_orderlines().filter(line => line.is_applied_promotion());
        return lines.reduce((acc, line) => {
        acc.push(...line.promotion_usage_ids); return acc;}, []);
    }

    _checkHasComboApplied() {
        return this._get_program_usage_ids().length > 0;
    }

    _checkHasNoMultiComboApplied() {
        let programs = this._get_program_usage_ids().map(p => this.pos.promotion_program_by_id[p.program_id]);
        return programs.some(p => p.apply_multi_program == false);
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
        for (const program of comboProgramToCheck) {
            var to_check_order_lines = this.get_orderlines_to_check().map(obj => ({...obj}));
            let NumberOfCombo = this._checkNumberOfCombo(program, to_check_order_lines, [] , 0)[2];
            if (NumberOfCombo >= 1) {
                comboProgramIsVerified[program.id] = NumberOfCombo;
            };
        };
        return comboProgramIsVerified;
    }

    get_orderlines_to_check() {
        return this.get_orderlines().filter(line => {
            if (line.is_reward_line) {
                return false;
            };
            if (line.promotion_usage_ids) {
                // Xóa chương trình đã áp dụng, nếu đã lưu trữ sau khi load lại đơn hàng từ Localstorage của browser
                if (line.promotion_usage_ids.some(usage => this.pos.promotion_program_by_id[usage.program_id] == undefined)) {
                    line.promotion_usage_ids = [];
                    line.reset_unit_price();
                    return true;
                }
                else if (line.promotion_usage_ids.some(pro => this.pos.promotion_program_by_id[pro.program_id].promotion_type == 'combo')) {
                    return false;
                };
            };
            return true;
        })
//        .sort((a,b) => b.product.lst_price - a.product.lst_price)
    }

    getActivatedComboPrograms() {
        return Array.from(this.activatedComboPrograms).map(proID => this.pos.promotion_program_by_id[proID]);
    }

    getPotentialProgramsToSelect() {
        let toCheck = this.pos.promotionPrograms;

        if (this._checkHasComboApplied()) {
            toCheck = toCheck.filter((p => !(p.apply_multi_program == false && p.promotion_type == 'combo')));
        };

        if (this._checkHasNoMultiComboApplied()) {
            toCheck = this.pos.promotionPrograms.filter(p => p.promotion_type !== 'combo');
        };

        var numberOfProgramsValues = this.verifyComboProgramOnOrder(toCheck);
        return Object.entries(numberOfProgramsValues)
                    .reduce((tmp, p) => {
                    tmp.push({
                        program : this.pos.promotionPrograms.find((pro)=> pro.id == p[0]),
                        number: p[1]
                    });
                    return tmp;
                    }, []);
    }

    _computeNewPriceForComboProgram(disc_total, base_total, prePrice, quantity) {
        let subTotalLine = prePrice * quantity;
        let discAmount = base_total > 0.0 ? subTotalLine / base_total * disc_total : 0.0;
        let newPrice = (subTotalLine - discAmount) / quantity;
        return [newPrice, discAmount]
    }

    applyAProgramToLineVales(program, comboLineList, number_of_combo) {
        let code = null;
        let activatedCodeObj = this.activatedInputCodes.find(c => c.program_id === program.id)
        if (activatedCodeObj) {code = activatedCodeObj.id};

        comboLineList.forEach(line => {line['promotion_usage_ids'] = [];});
        // Combo: Mua Combo, giảm tiền
        if (program.reward_type == 'combo_amount' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = program.disc_amount;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, originalPrice, newPrice, discAmountInLine));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        // Mua combo giảm phần trăm
        else if (program.reward_type == 'combo_percent' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = base_total_amount * program.disc_percent / 100;
            if (program.disc_max_amount > 0) {
                disc_total_amount = disc_total_amount < program.disc_max_amount ? disc_total_amount : program.disc_max_amount;
            };
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, originalPrice, newPrice, discAmountInLine));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        // Mua 1 combo với giá cố định
        else if (program.reward_type == 'combo_fixed_price' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = base_total_amount - program.disc_fixed_price
            disc_total_amount = disc_total_amount > 0 ? disc_total_amount : 0;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, originalPrice, newPrice, discAmountInLine));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        // Mua Comboo càng nhiều càng giảm, theo tỷ lệ %
        else if (program.reward_type == 'combo_percent_by_qty' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let rewardLines = program.rewards.sort((l1, l2) => l2.disc_percent > l1.disc_percent);
            let applyRewardLine;
            for (let i = 0; i < rewardLines.length; i++) {
                if (number_of_combo >= rewardLines[i].quantity_min) {
                    applyRewardLine = rewardLines[i];
                };
            };
            let disc_total_amount = base_total_amount * applyRewardLine.disc_percent / 100;
            if (applyRewardLine.disc_max_amount > 0) {
                disc_total_amount = disc_total_amount < applyRewardLine.disc_max_amount ? disc_total_amount : applyRewardLine.disc_max_amount;
            }
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, originalPrice, newPrice, discAmountInLine));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        // Mua Comboo càng nhiều càng giảm, theo đơn giá cố đinh
        else if (program.reward_type == 'combo_fixed_price_by_qty' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let rewardLines = program.rewards.sort((l1, l2) => l2.disc_percent > l1.disc_percent);
            let applyRewardLine;
            for (let i = 0; i < rewardLines.length; i++) {
                if (number_of_combo >= rewardLines[i].quantity_min) {
                    applyRewardLine = rewardLines[i];
                };
            };
            let disc_total_amount = base_total_amount - applyRewardLine.disc_fixed_price;
            disc_total_amount = disc_total_amount > 0 ? disc_total_amount : 0.0;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, originalPrice, newPrice, discAmountInLine));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        return comboLineList;
    }
    // todo: Fix trường hợp tiền giảm lớn hơn tổng giá trị của Combo
    computeForListOfCombo(orderLines, listOfComboProgram) {
        let lines_to_check = orderLines;
        let to_apply_lines = {};
        let combo_count = {};
        for (const program of listOfComboProgram) {
            var [remainingOrderLines, to_discount_line_vals, numberOfCombo] = this._checkNumberOfCombo(program, orderLines, [], 0);
            lines_to_check = remainingOrderLines;
            // ---------------------------------------------------------------- //

            combo_count[program.id] = numberOfCombo;

            for (let i = 0; i < to_discount_line_vals.length; i++) {
                let result = this.applyAProgramToLineVales(program, to_discount_line_vals[i], numberOfCombo);
                if (to_apply_lines.hasOwnProperty(program.id) && combo_count.hasOwnProperty(program.id)) {
                    to_apply_lines[program.id].push(...result);
                }
                else {
                    to_apply_lines[program.id] = result;
                };

            };
        };
        let total_discount_per_program = {}
        return [to_apply_lines, orderLines, combo_count];
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

    _createLineFromVals(vals) {
//        vals['lst_price'] = vals['price'];
        const line = Orderline.create({}, {pos: this.pos, order: this, product: vals['product']});
        this.fix_tax_included_price(line);
        this.set_orderline_options(line, vals);
        return line;
    }

    _getNewLineValuesAfterDiscount(arg){
        let product = arg['product']
        let price = arg['price']
        return {
            product: product,
            price: round_decimals(price, this.pos.currency.decimal_places),
            tax_ids: product.tax_ids,
            promotion_usage_ids: arg.promotion_usage_ids,
            quantity: arg['quantity'],
            is_reward_line: false,
            merge: false,
        }
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