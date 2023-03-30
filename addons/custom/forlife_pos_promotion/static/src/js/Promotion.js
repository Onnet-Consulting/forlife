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
import field_utils from 'web.field_utils';

const _t = core._t;


export class PromotionUsageLine {
    /**
     * @param {number} id of promotion.program
     * @param {number} id id of promotion.code
     * @param {number} original_price: price before discount
     * @param {number} discount_amount: discount amount on per unit of measure
     */
    constructor(program_id, code_id=null,  pro_priceitem_id=null, original_price, new_price, discount_amount, programStrID) {
        this.program_id = program_id;
        this.code_id = code_id;
        this.pro_priceitem_id = pro_priceitem_id || null;
        this.original_price = original_price;
        this.new_price = new_price;
        this.discount_amount = discount_amount;
        this.str_id = programStrID;
    }
}

export class PosPromotionCode {
    constructor(code, id, program_id, partner_id, remaining_amount) {
        this.code = code;
        this.id = id || nextId--;
        this.program_id = program_id;
        this.partner_id = partner_id;
        this.remaining_amount = remaining_amount || 0;
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
        this.promotionPricelistItems = loadedData['promotion.pricelist.item'] || [];
        this.monthData = loadedData['month.data'] || [];
        this.dayofmonthData = loadedData['dayofmonth.data'] || [];
        this.dayofweekData = loadedData['dayofweek.data'] || [];
        this.hourData = loadedData['hour.data'] || [];
        this._loadPromotionData();
    }
    _loadPromotionData() {
        this.promotion_program_by_id = {};
        this.reward_line_by_id = {};
        this.pro_pricelist_item_by_id = {};
        var self = this;
        for (const program of this.promotionPrograms) {
            if (program.from_date) {
                program.from_date = new Date(program.from_date);
            };
            if (program.to_date) {
                program.to_date = new Date(program.to_date);
            };
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

            var daysOfMonth = program.dayofmonth_ids.reduce(function (accumulator, d) {
                var day = self.dayofmonthData.find((elem) => elem.id === d);
                accumulator.add(day.code);
                return accumulator
            }, new Set());
            program.applied_dates = daysOfMonth;

            var daysOfWeek = program.dayofweek_ids.reduce(function (accumulator, d) {
                var day = self.dayofweekData.find((elem) => elem.id === d);
                let code;
                // Fix master data dayOfWeeks
                if ([0, 1, 2, 3, 4, 5].includes(day.code)) {
                    code = day.code + 1
                } else if (day.code == 6) {
                    code = 0
                }
                accumulator.add(code);
                return accumulator
            }, new Set());
            program.applied_days = daysOfWeek;

            var hours = program.hour_ids.reduce(function (accumulator, h) {
                var hour = self.hourData.find((elem) => elem.id === h);
                accumulator.add(hour.code);
                return accumulator
            }, new Set());
            program.applied_hours = hours;

            program.comboFormula = [];
            program.rewards = [];
            program.pricelistItems = [];
            program.productPricelistItems = new Set();
            program.program_id = program.id;
            program.str_id = String(program.id);
            program.display_name = program.name
        };
        for (const item of this.promotionComboLines) {
            item.valid_product_ids = new Set(item.valid_product_ids);
            item.program_id = item.program_id[0];
            item.program = this.promotion_program_by_id[item.program_id];
            item.program.comboFormula.push(item);
        };
        for (const reward of this.rewardLines) {
            this.reward_line_by_id[reward.id] = reward;
            reward.program_id = reward.program_id[0];
            reward.program = this.promotion_program_by_id[reward.program_id];
            reward.program.rewards.push(reward);
        };
        for (let item of this.promotionPricelistItems) {
            let str_id = `${item.program_id[0]}p${item.id}`;
            this.pro_pricelist_item_by_id[str_id] = item;
            item.product_id = item.product_id[0];
            item.str_id = str_id;
            item.program_id = item.program_id[0];
            item.program = this.promotion_program_by_id[item.program_id];
            item.program.pricelistItems.push(item);
            item.program.productPricelistItems.add(item.product_id);
            let program_clone = {...item.program};
            delete program_clone.id;
            delete program_clone.str_id;
            item = Object.assign(item, program_clone);
            item.display_name = item.display_name + ': ' + this.db.product_by_id[item.product_id].display_name;
        };
    }

    get_program_by_id(str_id) {
        if (str_id.includes('p')) {
            let [pId, itemId] = str_id.split('p');
            return this.promotionPricelistItems.find(p => p.id == itemId)
        } else {
            return this.promotionPrograms.find(p=>p.id == str_id)
        }
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

    constructor(obj, options) {
        super(...arguments);
        this.promotion_usage_ids = this.promotion_usage_ids || [];
        this.is_reward_line = options.is_reward_line || false;
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
                    item.pro_priceitem_id,
                    item.original_price,
                    item.new_price,
                    item.discount_amount,
                    item.str_id
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

    clone() {
        var orderline = super.clone();
        orderline.promotion_usage_ids = [...this.promotion_usage_ids];
        return orderline;
    }

    get_original_price() {
        return this.product.get_display_price(this.order.pricelist, 1)
    }

    get_total_discounted() {
        if (!this.promotion_usage_ids) {
            return 0.0
        }
        let result = this.promotion_usage_ids.reduce((accum, usage) => {return accum + usage.discount_amount * this.quantity;}, 0.0)
        return result || 0.0;
    }

    _isDiscountedComboProgram() {
        return this.promotion_usage_ids.some(pro => pro.discount_amount * this.quantity > 0.0)
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
        for (const usage of this.promotion_usage_ids) {
            result.push({id: usage.program_id, str: this.pos.get_program_by_id(usage.str_id).display_name});
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
        let activatedPricelistItem = new Set(this.activatedPricelistItem);
        json.activatedComboPrograms = [...activatedCombo];
        json.activatedCodePrograms = [...activatedCode];
        json.activatedPricelistItem = [...activatedPricelistItem];
        json.activatedInputCodes = this.activatedInputCodes;
        return json;
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.activatedComboPrograms = new Set(json.activatedComboPrograms);
        this.activatedCodePrograms = new Set(json.activatedCodePrograms);
        this.activatedPricelistItem = new Set(json.activatedPricelistItem);
        this.activatedInputCodes = json.activatedInputCodes;
        this.get_history_program_usages();
        this.historyProgramUsages = this.historyProgramUsages != undefined ? this.historyProgramUsages : {}
        this._resetPromotionPrograms();
    }
    /**
     * @override
     */
    async set_partner(partner) {
        const oldPartner = this.get_partner();
        super.set_partner(partner);
        if (oldPartner !== this.get_partner()) {
            await this.get_history_program_usages();
            this.activatedInputCodes = [];
            this._updateActivatedPromotionPrograms();
        };
    }

    async get_history_program_usages() {
        var self = this;
        const customer = this.get_partner();
        let programs = Object.keys(this.pos.promotion_program_by_id);
        await this.pos.env.services.rpc({
            model: 'pos.config',
            method: 'get_history_program_usages',
            args: [
                [this.pos.config.id],
                customer ? customer.id : false,
                programs
            ],
            kwargs: { context: session.user_context },
        }).then((result) => {
            self.historyProgramUsages = result || {};
        });
    }

    _programIsApplicableAutomatically(program) {

        if (program.with_code) {
            if (this.activatedInputCodes) {
                if (!this.activatedInputCodes.map(code => code.program_id).includes(program.id)) {return false;};
            } else {return false;};
        };
        const customer = this.partner;
        if (!program.valid_customer_ids.has(customer ? customer.id : 0)) {return false;};

        if (program.to_date && program.to_date <= new Date()) {
            return false;
        };
        if (program.from_date && program.from_date >= new Date()) {
            return false;
        };
        var hasDate = program.applied_dates.has(this.creation_date.getDate()) || program.applied_dates.size == 0;
        var hasMonth = program.applied_months.has(this.creation_date.getMonth() + 1) || program.applied_months.size == 0;
        var hasHour = program.applied_hours.has(this.creation_date.getHours()) || program.applied_hours.size == 0;
        var hasDay = program.applied_days.has(this.creation_date.getDay()) || program.applied_days.size == 0;
        if (!hasDate || !hasMonth || !hasHour || !hasDay) {;return false};
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
        line.is_cart_discounted = options.is_cart_discounted || false;
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
        if (!this.activatedPricelistItem) {
            this.activatedPricelistItem = new Set();
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
            this.activatedPricelistItem = new Set();
        }
        this._get_reward_lines().forEach(reward_line => {
            this.orderlines.remove(reward_line);
        })
//        this.remove_orderline(this._get_reward_lines()); // TODO: Xác định reward line của CTKM nào
        let orderlines = this.orderlines.filter(line => line._isDiscountedComboProgram())
        orderlines.forEach(line => line.reset_unit_price());
        orderlines.forEach(line => line.promotion_usage_ids = []);

        this._updateActivatedPromotionPrograms();
    }

    _get_reward_lines_of_cart_pro() {
        const orderLines = super.get_orderlines(...arguments);
        if (orderLines) {
            return orderLines.filter((line) => line.is_reward_line && line.is_cart_discounted);
        }
        return orderLines;
    }

    _resetCartPromotionPrograms() {
        this.orderlines.remove(this._get_reward_lines_of_cart_pro()); // TODO: Xác định reward line của CTKM nào
        let orderlines = this.orderlines.filter(line => line.is_cart_discounted);
        orderlines.forEach(line => line.reset_unit_price());
        orderlines.forEach(line => line.promotion_usage_ids = []);
        orderlines.forEach(line => line.is_cart_discounted = false);
        this._updateActivatedPromotionPrograms();
    }

    async _updateActivatedPromotionPrograms() {
        this.activatedComboPrograms = new Set();
        this.activatedCodePrograms = new Set();
        this.activatedPricelistItem = new Set();
        let validPromotionPrograms = this.verifyProgramOnOrder(this.pos.promotionPrograms);
        for (let proID of Object.keys(validPromotionPrograms)) {
            if (proID.includes('p') && this.pos.get_program_by_id(proID).promotion_type === 'pricelist') {
                this.activatedPricelistItem.add(proID);
            } else if (this.pos.get_program_by_id(proID).promotion_type === 'combo') {
                this.activatedComboPrograms.add(parseInt(proID));
            } else if (this.pos.get_program_by_id(proID).promotion_type === 'code') {
                this.activatedCodePrograms.add(parseInt(proID));
            };
        };
    }

    getActivatedPrograms() {
        let result = [];
        result.push(...Array.from(this.activatedComboPrograms).map(proID => this.pos.promotion_program_by_id[proID]));
        result.push(...Array.from(this.activatedCodePrograms).map(proID => this.pos.promotion_program_by_id[proID]));
        result.push(...Array.from(this.activatedPricelistItem).map(proID => this.pos.pro_pricelist_item_by_id[proID]));
        return result;
    }

    getValidProgramsOnOrder() { // todo: check usage???
        let toCheck = this.pos.promotionPrograms;
        var numberOfProgramsValues = this.verifyProgramOnOrder(toCheck);
        return Object.keys(numberOfProgramsValues).reduce((tmp, p) => {tmp.push(p); return tmp}, tmp);
    }

    getPotentialProgramsToSelect() {
        let toCheck = this.getActivatedPrograms();
        var numberOfProgramsValues = this.verifyProgramOnOrder(toCheck);
        return Object.entries(numberOfProgramsValues)
                    .reduce((tmp, p) => {
                    tmp.push({
                        program : this.pos.get_program_by_id(p[0]),
                        number: p[1]
                    });
                    return tmp;
                    }, []);
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
                cid: l.cid,
                price: l.price,
                full_product_name: l.full_product_name,
                tax_ids: [...(l.tax_ids || [])]
            });
        })
        return lines;
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
                };
            };
            return true;
        });
    }


    _get_program_usage_ids() {
        let lines = this.get_orderlines().filter(line => line.is_applied_promotion());
        return lines.reduce((acc, line) => {
        acc.push(...line.promotion_usage_ids); return acc;}, []);
    }

    _getPricelistItem(product) {
        let programs = this.getValidProgramsOnOrder().filter(p => p.promotion_type == 'pricelist');
        let pricelistItem;
        for (program in programs) {
            pricelistItem = program.productPricelistItems.find(item => item.product_id === product.id);
            if (pricelistItem) {
                return pricelistItem;
            };
        };
        return false;
    }

    _getNumberOfComboApplied() {
//        {program_combo_id: int, ...}
        let result = {};
        for (let line of this.get_orderlines_to_check()) {
            for (let usage of line.promotion_usage_ids) {
                if (this.pos.promotion_program_by_id[usage.program_id].promotion_type == 'combo'){
                    if (usage.program_id in result) {
                        result[usage.program_id] += line.quantity;
                    } else {
                        result[usage.program_id] = line.quantity;
                    };
                };
            };
        };
        Object.entries(result).forEach(([k,v]) => {
            let program = this.pos.promotion_program_by_id[k];
            v = v/program.qty_per_combo;
            result[k] = v;
        });
        return result
    }

    // Filter based on promotion_usage_ids
    _filterOrderLinesToCheckComboPro(order_lines) {
        return order_lines.filter(l => {
            for (let usage of l.promotion_usage_ids) {
                let program = this.pos.get_program_by_id(usage.str_id);
                if (['pricelist', 'combo'].includes(program.promotion_type)) {return false};
                if (program == 'code' && program.discount_based_on == 'unit_price') {return false};
            };
            return true;
        });
    }

    _filterOrderLinesToCheckCodePro(pro, order_lines) {
        if (pro.promotion_type == 'code' && pro.discount_based_on == 'unit_price') {
            return order_lines.filter(function(l) {
                return l.promotion_usage_ids || l.promotion_usage_ids.length == 0 ? true : false;
            });
        } else if (pro.promotion_type == 'code' && pro.discount_based_on == 'discounted_price') {
            return order_lines.filter(function(l) {
                if (l.promotion_usage_ids) {
                    return l.promotion_usage_ids.some(p => p.promotion_type == 'pricelist' || (p.promotion_type == 'pricelist' && p.discount_based_on == 'unit_price')) ? true : false;
                } else {return true};
            });
        };
        return order_lines
    }

    _filterOrderLinesToCheckPricelistPro(pricelistItem, order_lines) {
        let filtered_orderline = order_lines.filter(l => {
            return !l.promotion_usage_ids || l.promotion_usage_ids.length == 0 ? true : false;
        });
        return filtered_orderline.filter(line => line.product.id === pricelistItem.product_id);
    }

    _checkNumberOfCode(codeProgram, order_lines, to_discount_line_vals , count, max_count = false) {
        let to_check_order_lines = this._filterOrderLinesToCheckCodePro(codeProgram, order_lines);
        count = count || 0;
        to_discount_line_vals = to_discount_line_vals || [];
        let result = [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count];
        var valid_product_ids = codeProgram.valid_product_ids;

        if (codeProgram.reward_type == "code_amount") {
            max_count = 1;
        }

        to_check_order_lines.sort((a,b) => (a.product.lst_price < b.product.lst_price) ? 1 : ((b.product.lst_price < a.product.lst_price) ? -1 : 0))
        var oneCombo = [];
        var decimals = this.pos.dp['Product Unit of Measure'];
        for (const ol of to_check_order_lines.filter(ol => !valid_product_ids.size || (valid_product_ids.has(ol.product.id)  && ol.quantity >= codeProgram.min_quantity))) {
            var quantity_combo = Math.floor(ol.quantity / codeProgram.min_quantity)
            if (max_count && count + quantity_combo >= max_count){
                quantity_combo = max_count - count
            }
            for (var i =0; i<quantity_combo; i++) {
                to_discount_line_vals.push({
                    product: ol.product,
                    quantity:  codeProgram.min_quantity,
                    price: ol.product.lst_price,
                    isNew: true,
                    promotion_usage_ids: [...ol.promotion_usage_ids]
                });
            }
            ol.quantity = ol.quantity - quantity_combo * codeProgram.min_quantity;
            ol.quantityStr = field_utils.format.float(ol.quantity, {digits: [69, decimals]});
            count += quantity_combo;
        }

        if (max_count && count >= max_count) {
            return [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count];
        }

        var order_lines_has_valid_product = to_check_order_lines.filter(l => !valid_product_ids.size || valid_product_ids.has(l.product.id));

        var oneCombo = [];
        var total_quantity = order_lines_has_valid_product.reduce((q, {quantity}) => q + quantity, 0);
        var min_quantity_tmp = codeProgram.min_quantity
        if (total_quantity >= codeProgram.min_quantity) {
            for (const ol of order_lines_has_valid_product) {
                if (ol.quantity <= min_quantity_tmp) {
                    var quantity = ol.quantity;
                    min_quantity_tmp -= ol.quantity;
                    total_quantity -= ol.quantity;
                    to_discount_line_vals.push({
                        product: ol.product,
                        quantity:  quantity,
                        price: ol.product.lst_price,
                        isNew: true,
                        promotion_usage_ids: [...ol.promotion_usage_ids]
                    });
                    ol.quantity -= quantity;
                    ol.quantityStr = field_utils.format.float(ol.quantity, {digits: [69, decimals]});
                }
            }
            count++;
        }
        var total_price = to_discount_line_vals.reduce((p, {price, quantity}) => p + price*quantity, 0)
        for (const discount_line_val of to_discount_line_vals) {
            discount_line_val.total_price = total_price;
        }
        return [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count];
    }

    // TODO: Fix: sau tách các dòng đã có khuyến mãi, số tiền tổng khuyến mãi phỉa được tính lại cho chính xác theo tỷ lệ số lượng
    /*
    * recursion function
    * return {number} count of  combo
    */
    _checkNumberOfCombo(comboProgram, order_lines, to_discount_line_vals , count) {
        let to_check_order_lines = this._filterOrderLinesToCheckComboPro(order_lines);
        count = count || 0;
        to_discount_line_vals = to_discount_line_vals || [];
        let result = [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count];
        // Check if combo formula is not defined
        var comboFormula = comboProgram.comboFormula;
        if (comboFormula.length == 0) {
            return result;
        };
        // Check if there is a limitation of number of combo applied program per order
        if (comboProgram.limit_usage_per_order) {
            let applied_per_order = (this._getNumberOfComboApplied()[comboProgram.id] || 0.0) + count;
            if  (comboProgram.limit_usage_per_order && applied_per_order >= comboProgram.max_usage_per_order) {
                return result;
            };
        };
        // Check if there is a limitation of number of combo applied program per customer
        if (comboProgram.limit_usage_per_customer) {
            let historyUsed = (this.historyProgramUsages || {})[comboProgram.id] || 0;
            let applied_per_customer = historyUsed + (this._getNumberOfComboApplied()[comboProgram.id] || 0.0) + count;
            if  (comboProgram.limit_usage_per_customer && applied_per_customer >= comboProgram.max_usage_per_customer) {
                return result;
            };
        };

        var enoughCombo = true;
        for (const part of comboFormula) {
            var order_lines_has_valid_product = to_check_order_lines.filter(l => part.valid_product_ids.has(l.product.id));
            var qty_total = order_lines_has_valid_product.reduce((accumulator, l) => accumulator + l.quantity, 0);
            if (qty_total < part.quantity) {enoughCombo = false; break;};
        };
        if (enoughCombo == false) {
            return result;
        } else {
            var oneCombo = []
            for (const part of comboFormula) {
                var qty_to_take_on_candidates = part.quantity
                for (const ol of to_check_order_lines.filter(ol => part.valid_product_ids.has(ol.product.id)  && ol.quantity > 0)) {
                    var qty_taken_on_candidate = Math.min(qty_to_take_on_candidates, ol.quantity);
                    /* ============ */
                    ol.quantity = ol.quantity - qty_taken_on_candidate;
                    oneCombo.push({
                        product: ol.product,
                        quantity: qty_taken_on_candidate,
                        price: ol.product.lst_price,
                        isNew: true,
                        promotion_usage_ids: [...ol.promotion_usage_ids]
                    });
                    qty_to_take_on_candidates -= qty_taken_on_candidate;
                    if (qty_to_take_on_candidates <= 0.0) {break;};
                };
            };
            to_discount_line_vals.push(oneCombo);
            return this._checkNumberOfCombo(comboProgram, order_lines, to_discount_line_vals, count + 1);
        };
    }

    _checkQtyOfProductForPricelist(pricelistItem, orderLines) {
        let to_check_order_lines = this._filterOrderLinesToCheckPricelistPro(pricelistItem, orderLines);
        let qty = 0.0;
        let to_discount_line_vals = [];
        for (let line of to_check_order_lines) {
            if (line.quantity > 0) {
                qty += line.quantity;
                to_discount_line_vals.push({
                        product: line.product,
                        quantity: line.quantity,
                        price: line.product.lst_price,
                        isNew: true,
                        promotion_usage_ids: [...line.promotion_usage_ids]
                    });
                line.quantity = 0;

            }
        };
        return [orderLines, to_discount_line_vals, qty]
    }

    _compute_discounted_total_clone(line) {
        if (!line.promotion_usage_ids) {
            return 0.0;
        };
        let result = line.promotion_usage_ids.reduce((accum, usage) => {return accum + usage.discount_amount * line.quantity;}, 0.0);
        return result || 0.0;
    }

    _get_program_ids_in_usages(line) {
        return line.promotion_usage_ids.reduce((acc, usage) => {acc.add(usage.program_id); return acc}, new Set())
    }

    arrayIsChild(array, subArray) {
        if (!subArray) {return false};
        return subArray.every((element, i, arr) => {return _.isEqual(element, array.at(i));});
    }

    arrayIsSame(array, subArray) {
        let i = 0;
        for (let subEl of subArray) {
            let currentIndex = array.indexOf(subEl)
            if (currentIndex < i) {
                return false;
            } else {
                i = currentIndex;
            }
        };
        return true;
    }

//    checkHasSubArray(master, sub, no) {
//        return sub.length < no && sub.every((i => v => i = master.indexOf(v, i) + 1)(0));
//    }

    permutator(inputArr) {
        let accumValidCombs = [];
        let max = 0.0;
        let result = null;
        const permute = (arr, m = []) => {
            if (arr.length === 0) {
                let hasChecked = accumValidCombs.some((comb, i, a) => {
                        return this.arrayIsChild(m, comb);
                });
                if (!hasChecked && accumValidCombs.some((comb) => {return this.arrayIsSame(m, comb) && comb.length >= 5;})) {
                    hasChecked = true;
                };
                if (!hasChecked) {
                    let [validCombine, disc] = this._computeBestCombineOfProgram([m]);
                    let check = accumValidCombs.some(c => _.isEqual(validCombine.at(0), c))
                    if (!check) {
                        accumValidCombs.push(...validCombine);
                        if (disc > max) {
                            max = disc;
                            result = validCombine.at(0);
                        };
                    };
                };
            }
            else {
                for (let i = 0; i < arr.length; i++) {
                    let curr = arr.slice();
                    let next = curr.splice(i, 1);
                        permute(curr.slice(), m.concat(next));
                };
            };
        };
        permute(inputArr);
        return result;
    }

    computeBestCombineOfProgram(){
        let programs = this.getActivatedPrograms().map(p => p.str_id);
        console.log('programs', programs);
        if (programs.length > 8) {
            return [];
        };
        let programs_combines = this.permutator(programs);
        console.log(programs_combines);
        return programs_combines;
    }

    _computeBestCombineOfProgram(programs_combines) {
        var _get_program_ids_in_usages = (line) => line.promotion_usage_ids.reduce((acc, usage) => {acc.push(usage.str_id); return acc}, [])
        let result = [];
        let max = 0;
        for (let combination of programs_combines) {
            combination = combination.map(p => this.pos.get_program_by_id(p));
            let clone_order_lines = this.pos.get_order().get_orderlines_to_check().map(obj => ({...obj}));
            let [discount_lines_1, discount_lines_2, c] = this.computeForListOfProgram(clone_order_lines, combination);
            let discount_lines = [...Object.values(discount_lines_1).flat(2), ...discount_lines_2];
            let discounted_total = discount_lines.reduce((acc, line) => {acc += this._compute_discounted_total_clone(line); return acc}, 0);
            let usage_programs = discount_lines.reduce((acc, line) => {
                    _get_program_ids_in_usages(line).forEach(el => acc.add(this.pos.get_program_by_id(el))); return acc
                    }, new Set()
                );
            if (discounted_total > max) {
                result = [combination.filter(p => usage_programs.has(p)).map(p => p.str_id)];
                max = discounted_total
            };
        };
        return [result, max];
    }

    /* return {<program_id>: number_of_combo}*/
    verifyProgramOnOrder(toVerifyPromotionPrograms) {
        var comboProgramToCheck = new Set();
        var programIsVerified = new Object();
        for (const program of toVerifyPromotionPrograms) {
            if (this._programIsApplicableAutomatically(program) && program.promotion_type != 'cart') {
                comboProgramToCheck.add(program);
            };
        };
        for (const program of comboProgramToCheck) {
            if (program.promotion_type == 'combo') {
                let to_check_order_lines = this.get_orderlines_to_check().map(obj => ({...obj}));
                let NumberOfCombo = this._checkNumberOfCombo(program, to_check_order_lines, [] , 0)[2];
                if (['combo_percent_by_qty', 'combo_fixed_price_by_qty'].includes(program.reward_type) && !(NumberOfCombo >= program.qty_min_required)) {
                    continue;
                };
                if (NumberOfCombo >= 1) {
                    programIsVerified[program.str_id] = NumberOfCombo;
                };
            }
            else if (program.promotion_type == 'code') {
                var to_check_order_lines = this.get_orderlines_to_check().map(obj => ({...obj}));
                let NumberOfCombo = this._checkNumberOfCode(program, to_check_order_lines, [] , 0)[2];
                if (NumberOfCombo >= 1) {
                    programIsVerified[program.id] = NumberOfCombo;
                };
            }
            else if (program.promotion_type == 'pricelist') {
                for (let priceItem of program.pricelistItems) {
                    let to_check_order_lines = this.get_orderlines_to_check().map(obj => ({...obj}));
                    let QtyOfProduct = this._checkQtyOfProductForPricelist(priceItem, to_check_order_lines)[2];

                    if (QtyOfProduct > 0) {
                        programIsVerified[priceItem.str_id] = QtyOfProduct;
                    };
                };
            };
        };
        return programIsVerified;
    }

    _apply_cart_program_to_orderline(program, to_discount_lines) {
        if (program.reward_type == 'cart_get_voucher') {
            // pass
        }
        else if (program.reward_type == 'cart_discount_percent') {
            for (let line of to_discount_lines) {
                let originalPrice = line.price;
                let discAmount = line.price * program.disc_percent/100;
                let newPrice = originalPrice - discAmount;
                line.price = newPrice;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                program.id, null, null, originalPrice, newPrice, discAmount, program.str_id));
                line.is_cart_discounted = true;
            }
        }
        else if (program.reward_type == 'cart_discount_fixed_price') {
            for (let line of to_discount_lines) {
                let originalPrice = line.price;
                let newPrice = program.disc_fixed_price;
                let discAmount = originalPrice - newPrice;
                line.price = newPrice;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                program.id, null, null, originalPrice, newPrice, discAmount, program.str_id));
                line.is_cart_discounted = true;
            }
        }
        else if (program.reward_type == 'cart_get_x_free') {
            for (let line of to_discount_lines) {
                let originalPrice = line.price
                let newPrice = 0.0
                let discAmount = originalPrice - newPrice
                line.price = newPrice;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                program.id, null, null, originalPrice, newPrice, discAmount, program.str_id));
                line.is_cart_discounted = true;
            }
        }
        return to_discount_lines
    }

    _checkNumberOfProductInCartProgram(program, orderLines, selectedVals) {
        let to_discount_line_vals = [];
        for (let [cid, qty_taken] of Object.entries(selectedVals)) {
            let line = orderLines.find(l => l.cid == cid);
            line.quantity = line.quantity - qty_taken;
            to_discount_line_vals.push({
                product: line.product,
                quantity: qty_taken,
                price: line.product.lst_price,
                isNew: true,
                promotion_usage_ids: [...line.promotion_usage_ids]
            });
        }
        return [to_discount_line_vals, orderLines]
    }

    // return: discount_amount
    _get_discount_amount_cart_program(program, line) {
        if (program.reward_type == 'cart_discount_percent') {
            let disc_amount = line.price * program.disc_percent;
            disc_amount = program.disc_max_amount > 0 && program.disc_max_amount < disc_amount && program.disc_max_amount || disc_amount;
            return disc_amount;
        }
        else if (program.reward_type == 'cart_discount_fixed_price') {
        }
        else if (program.reward_type == 'cart_get_x_free') {
        }
    }
    // orderLine of Order: clone or real
    // listOfProgram
    /*
    / @param: {proID : [{line_ID: qty_to_apply},...]}
    / @return: {proID: boolean}
    */
    computeForListOfCartProgram(orderLines, listOfProgram) {
        let to_apply_lines = {};
        let programs = Object.entries(listOfProgram);
        for (let [program_id, selectedVals] of programs) {
            let program = this.pos.get_program_by_id(program_id);
            let [to_discount_line_vals, remainingOrderLines] = this._checkNumberOfProductInCartProgram(program, orderLines, selectedVals);
            let result = this._apply_cart_program_to_orderline(program, to_discount_line_vals);
            if (to_apply_lines.hasOwnProperty(program.id)) {
                to_apply_lines[program.id].push(...result);
            } else {
                to_apply_lines[program.id] = result;
            }
        }
        return [to_apply_lines, orderLines];
    }

    verifyCardProgramOnOrder(orderLines) {
        const cardPrograms = this.pos.promotionPrograms.filter(p=> p.promotion_type == 'cart');
        const totalTaxed = this.get_total_with_tax();
        const totalUntaxed = this.get_total_without_tax();
        const totalsPerProgram = Object.fromEntries(cardPrograms.map((program) => [program.id, {'untaxed': totalUntaxed, 'taxed': totalTaxed}]));

        let result = [];
        for (let program of cardPrograms) {
            if (!this._programIsApplicableAutomatically(program)) {
                continue
            };

            const amountCheck = totalsPerProgram[program.id]['taxed']
            if (program.order_amount_min > amountCheck) {
                continue;
            };
            let to_check_products = program.valid_product_ids.size > 0;
            let qty_taken = 0;
            for (const line of orderLines) {
                if (!line.is_reward_line && program.valid_product_ids.has(line.product.id)) {
                    qty_taken += line.quantity;
                };
            };
            if (to_check_products && qty_taken < program.min_quantity) {
                continue;
            };
            let to_discount_lines = [];
            let to_reward_lines = [];
            let vouchers = [];
            if (program.reward_type == 'cart_get_x_free') {
                to_reward_lines = orderLines.filter(l=>!l.is_applied_promotion() && l.quantity > 0).filter(l=>program.reward_product_ids.has(l.product.id));
            } else if (program.reward_type == 'cart_get_voucher') {
                vouchers = [];
            } else {
                to_discount_lines = orderLines.filter(l=>!l.is_applied_promotion() && l.quantity > 0).filter(l=>program.discount_product_ids.has(l.product.id));
            };
            result.push({
                id: program.id,
                program: program,
                vouchers,
                to_reward_lines,
                to_discount_lines,
                isSelected: false
            });
        };
        return result
    }

    _computeNewPriceForComboProgram(disc_total, base_total, prePrice, quantity) {
        let subTotalLine = prePrice * quantity;
        let discAmountInLine = base_total > 0.0 ? subTotalLine / base_total * disc_total : 0.0;
        let discAmount = discAmountInLine / quantity;
        let newPrice = (subTotalLine - discAmountInLine) / quantity;
        return [newPrice, discAmount]
    }

    applyAPricelistProgramToLineVales(PricelistItem, LineList, number_of_product) {
        for (let line of LineList) {
            let oldPrice = line.price;
            let fixed_price = PricelistItem.fixed_price;
            let discount_amount = (line.price - fixed_price);
            if (discount_amount > 0) {
                line.price = fixed_price;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                    PricelistItem.program_id,
                    null,
                    PricelistItem.id,
                    oldPrice,
                    fixed_price,
                    discount_amount,
                    PricelistItem.str_id
                ));
            };
        };
        return LineList;
    }

    applyACodeProgramToLineVales(CodeProgram, LineList, number_of_product, remaining_amount) {
        let code = null;
        let activatedCodeObj = this.activatedInputCodes.find(c => c.program_id === CodeProgram.id)
        if (activatedCodeObj) {code = activatedCodeObj.id};

        if (CodeProgram.reward_type == "code_amount") {
            let total_price = LineList.total_price;
//            if (CodeProgram.discount_apply_on == "order") {
//                total_price = LineList.order.
//            }
            if (remaining_amount === false) {
                remaining_amount = activatedCodeObj.remaining_amount;
            }

            let base_total_amount = LineList.quantity*LineList.price;
            let disc_total_amount = round_decimals(CodeProgram.disc_amount * base_total_amount/total_price, this.pos.currency.decimal_places);

            if (remaining_amount <= disc_total_amount) {
                disc_total_amount = remaining_amount;
                remaining_amount = 0;
            } else {
                remaining_amount -= disc_total_amount;
            }

            if (disc_total_amount > 0) {
                let originalPrice = LineList.price;
                let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, LineList.quantity);
                LineList.price = newPrice;
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null,originalPrice, newPrice, discAmountInLine, CodeProgram.str_id));
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${CodeProgram.name}.`), 3000);
            };
        } else if (CodeProgram.reward_type == "code_percent") {
            if (remaining_amount === false) {
                remaining_amount = activatedCodeObj.remaining_amount;
            }
            let base_total_amount = LineList.quantity*LineList.price;
            let disc_total_amount = round_decimals(base_total_amount * CodeProgram.disc_percent / 100, this.pos.currency.decimal_places);

            if (remaining_amount <= disc_total_amount) {
                disc_total_amount = remaining_amount;
                remaining_amount = 0;
            } else {
                remaining_amount -= disc_total_amount;
            }

            if (disc_total_amount > 0) {
                let originalPrice = LineList.price;
                let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, LineList.quantity);
                LineList.price = newPrice;
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null,originalPrice, newPrice, discAmountInLine, CodeProgram.str_id));
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${CodeProgram.name}.`), 3000);
            };
        } else if (CodeProgram.reward_type == "code_fixed_price") {
            let base_total_amount = LineList.quantity*LineList.price;
            let disc_total_amount = base_total_amount - CodeProgram.disc_fixed_price
            disc_total_amount = disc_total_amount > 0 ? disc_total_amount : 0;

            if (disc_total_amount > 0) {
                let originalPrice = LineList.price;
                let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, LineList.quantity);
                LineList.price = newPrice;
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null,originalPrice, newPrice, discAmountInLine, CodeProgram.str_id));
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${CodeProgram.name}.`), 3000);
            };
        } else if (CodeProgram.reward_type == "code_buy_x_get_y") {
            LineList.reward_products = {
                'reward_product_ids': CodeProgram.reward_product_ids,
                'qty': CodeProgram.reward_quantity
            }
        } else if (CodeProgram.reward_type == "code_buy_x_get_cheapest") {
            LineList.reward_products = {
                'qty': CodeProgram.reward_quantity
            }
        }

        return [[LineList], remaining_amount];
    }

    // For Combo Program
    applyAComboProgramToLineVales(program, comboLineList, number_of_combo) {
        let code = null;
        let activatedCodeObj = this.activatedInputCodes.find(c => c.program_id === program.id)
        if (activatedCodeObj) {code = activatedCodeObj.id};

        comboLineList.forEach(line => {
            line['promotion_usage_ids'] = line['promotion_usage_ids'] == undefined ? [] : line['promotion_usage_ids'];
        });
        // Combo: Mua Combo, giảm tiền
        if (program.reward_type == 'combo_amount' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = program.disc_amount;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id));
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
                    let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id));
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
                    let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        // Mua Comboo càng nhiều càng giảm, theo tỷ lệ %
        else if (program.reward_type == 'combo_percent_by_qty' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let rewardLines = program.rewards.sort((l1, l2) => l2.quantity_min - l1.quantity_min);
            let applyRewardLine;
            for (let i = 0; i < rewardLines.length; i++) {
                if (number_of_combo >= rewardLines[i].quantity_min) {
                    applyRewardLine = rewardLines[i];
                    break;
                };
            };
            if (!applyRewardLine) {
                return comboLineList;
            };
            let disc_total_amount = base_total_amount * applyRewardLine.disc_percent / 100;
            if (applyRewardLine.disc_max_amount > 0) {
                disc_total_amount = disc_total_amount < applyRewardLine.disc_max_amount ? disc_total_amount : applyRewardLine.disc_max_amount;
            }
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        // Mua Comboo càng nhiều càng giảm, theo đơn giá cố đinh
        else if (program.reward_type == 'combo_fixed_price_by_qty' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let rewardLines = program.rewards.sort((l1, l2) => l2.quantity_min - l1.quantity_min);
            let applyRewardLine;
            for (let i = 0; i < rewardLines.length; i++) {
                if (number_of_combo >= rewardLines[i].quantity_min) {
                    applyRewardLine = rewardLines[i];
                    break;
                };
            };
            if (!applyRewardLine) {
                return comboLineList;
            };
            let disc_total_amount = base_total_amount - applyRewardLine.disc_fixed_price;
            disc_total_amount = disc_total_amount > 0 ? disc_total_amount : 0.0;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id));
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        return comboLineList;
    }
    // Compute and Apply Order With list of Combo Program
    computeForListOfProgram(orderLines, listOfComboProgram) {
        let to_apply_lines = {};
        let combo_count = {};
        for (const program of listOfComboProgram) {
            // Combo Program
            if (program.promotion_type == 'combo') {
                if (program.reward_type == 'combo_amount') {
                    orderLines.sort((a,b) => a.product.lst_price - b.product.lst_price)
                } else {
                    orderLines.sort((a,b) => b.product.lst_price - a.product.lst_price)
                };
                var [remaining, to_discount_line_vals, numberOfCombo] = this._checkNumberOfCombo(program, orderLines, [], 0);

                combo_count[program.id] = numberOfCombo;

                for (let i = 0; i < to_discount_line_vals.length; i++) {
                    let result = this.applyAComboProgramToLineVales(program, to_discount_line_vals[i], numberOfCombo);
                    if (to_apply_lines.hasOwnProperty(program.id) && combo_count.hasOwnProperty(program.id)) {
                        to_apply_lines[program.str_id].push(...result);
                    } else {
                        to_apply_lines[program.str_id] = result;
                    };
                };
            }
            // Code Program
            else if (program.promotion_type == 'code') {
                if (program.reward_type == 'code_amount') {
                    orderLines.sort((a,b) => a.product.lst_price - b.product.lst_price)
                } else {
                    orderLines.sort((a,b) => b.product.lst_price - a.product.lst_price)
                };
                var [remaining, to_discount_line_vals, numberOfCombo] = this._checkNumberOfCode(program, orderLines, [], 0);

                combo_count[program.id] = numberOfCombo;

                var remaining_amount = false;

//                if (program.reward_type == 'code_amount' && program.discount_apply_on == "order" && numberOfCombo) {
//                    for (let i = 0; i < orderLines.length; i++) {
//                        let result;
//                        [result, remaining_amount] = this.applyACodeProgramToLineVales(program, orderLines[i], numberOfCombo, remaining_amount);
//                        if (to_apply_lines.hasOwnProperty(program.id) && combo_count.hasOwnProperty(program.id)) {
//                            to_apply_lines[program.id].push(...result);
//                        } else {
//                            to_apply_lines[program.id] = result;
//                        };
//                    };
//                } else {
                    for (let i = 0; i < to_discount_line_vals.length; i++) {
                        let result;
                        [result, remaining_amount] = this.applyACodeProgramToLineVales(program, to_discount_line_vals[i], numberOfCombo, remaining_amount);
                        if (to_apply_lines.hasOwnProperty(program.id) && combo_count.hasOwnProperty(program.id)) {
                            to_apply_lines[program.id].push(...result);
                        } else {
                            to_apply_lines[program.id] = result;
                        };
                    };
//                }
            }
            // Pricelist Program
            else if (program.promotion_type == 'pricelist') {
                let [ols, to_discount_line_vals, qty] = this._checkQtyOfProductForPricelist(program, orderLines);
                let result = this.applyAPricelistProgramToLineVales(program, to_discount_line_vals, qty);
                combo_count[program.str_id] = qty;
                if (to_apply_lines.hasOwnProperty(program.str_id) && combo_count.hasOwnProperty(program.str_id)) {
                        to_apply_lines[program.str_id].push(...result);
                    } else {
                        to_apply_lines[program.str_id] = result;
                };
            };
        };
        return [to_apply_lines, orderLines, combo_count];
    }

    async _activatePromotionCode(code) {

        if (!this.pos.promotionPrograms.some(p => p.promotion_type == 'code' || p.with_code == true)) {
            return _t('Not found an available Promotion Program needed Code to be activated');
        };

        if (this.activatedInputCodes.find((c) => c.code === code)) {
            return _t('That coupon code has already been scanned and activated.');
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
            const codeObj = new PosPromotionCode(code, payload.code_id, payload.program_id, payload.coupon_partner_id, payload.remaining_amount);
            this.activatedInputCodes.push(codeObj);
            await this._updateActivatedPromotionPrograms();
        } else {
            return payload.error_message;
        };
        return true;
    }

    _createLineFromVals(vals) {
//        vals['lst_price'] = vals['price'];
        const line = Orderline.create({}, {pos: this.pos, order: this, ...vals});
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
            is_reward_line: arg.is_reward_line,
            merge: false,
            is_cart_discounted: arg.is_cart_discounted
        }
    }

    async activatePromotionCode(code) {
        const res = await this._activatePromotionCode(code);
        if (res !== true) {
            Gui.showNotification(res);
        } else {
            Gui.showNotification(_t('Successfully activate a promotion code.'),3000);
        };
    }

}
Registries.Model.extend(Order, PosPromotionOrder);