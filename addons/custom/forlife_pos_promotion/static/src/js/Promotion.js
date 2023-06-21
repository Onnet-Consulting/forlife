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
import utils from 'web.utils';
const _t = core._t;
var round_di = utils.round_decimals;

export class PromotionUsageLine {
    /**
     * @param {number} id of promotion.program
     * @param {number} id id of promotion.code
     * @param {number} original_price: price before discount
     * @param {number} discount_amount: discount amount on per unit of measure
     */
    constructor(program_id, code_id=null,  pro_priceitem_id=null, original_price, new_price, discount_amount, programStrID, promotion_type, discount_based_on) {
        this.program_id = program_id;
        this.code_id = code_id;
        this.pro_priceitem_id = pro_priceitem_id || null;
        this.original_price = original_price;
        this.new_price = new_price;
        this.discount_amount = discount_amount;
        this.str_id = programStrID;
        this.discount_based_on = discount_based_on || null;
        this.promotion_type = promotion_type || null;
    }
}

export class PosPromotionCode {
    constructor(code, id, program_id, partner_id, remaining_amount, reward_for_referring, reward_program_id, reward_program_name) {
        this.code = code;
        this.id = id || nextId--;
        this.program_id = program_id;
        this.partner_id = partner_id;
        this.remaining_amount = remaining_amount || 0;
        this.reward_for_referring = reward_for_referring;
        this.reward_program_id = reward_program_id;
        this.reward_program_name = reward_program_name;
    }
}

const PosPromotionGlobalState = (PosGlobalState) => class PosPromotionGlobalState extends PosGlobalState {
    //@override
    async _processData(loadedData) {
        this.couponCache = {};
        await super._processData(loadedData);
        this.promotionPrograms = loadedData['promotion.program'] || [];
        this.surprisingRewardProducts = loadedData['surprising.reward.product.line'] || [];
        this.promotionComboLines = loadedData['promotion.combo.line'] || [];
        this.rewardLines = loadedData['promotion.reward.line'] || [];
        this.monthData = loadedData['month.data'] || [];
        this.dayofmonthData = loadedData['dayofmonth.data'] || [];
        this.dayofweekData = loadedData['dayofweek.data'] || [];
        this.hourData = loadedData['hour.data'] || [];
        this.promotionPricelistItems = [];
        this._loadPromotionData();
        this.loadPromotionPriceListItemBackground();
    }
    _loadPromotionData() {
        this.promotion_program_by_id = {};
        this.reward_line_by_id = {};
        this.pro_pricelist_item_by_id = {};
//        this.pricelistProApplicableProducts = new Set(); // todo: use to estimate performance
        var self = this;
        for (const line of this.surprisingRewardProducts) {
            line.to_check_product_ids = new Set(line.to_check_product_ids);
        };
        for (const program of this.promotionPrograms) {
            if (program.from_date) {
                program.from_date = new Date(program.from_date);
            };
            if (program.to_date) {
                program.to_date = new Date(program.to_date);
            };
            let json_valid_product_ids_str = program.json_valid_product_ids ? program.json_valid_product_ids : "W10=";
            let valid_product_ids = JSON.parse(atob(json_valid_product_ids_str));
            program.valid_product_ids = new Set(valid_product_ids);
            program.valid_customer_ids = new Set();
            program.discount_product_ids = new Set(program.discount_product_ids);
            program.reward_product_ids = new Set(program.reward_product_ids);
            program.codes = {}; // {'access_token': CodeObject}

//            let json_pricelist_item_ids_str = program.json_pricelist_item_ids ? program.json_pricelist_item_ids : "W10=";
//            this.promotionPricelistItems = JSON.parse(atob(json_pricelist_item_ids_str)) || [];

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
                accumulator.add(day.code);
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
            let cl_valid_product_ids = JSON.parse(atob(item.json_valid_product_ids));
            item.valid_product_ids = new Set(cl_valid_product_ids);
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
    }

    async loadPromotionPriceListItemBackground() {
        let page = 0;
        let promotionItems = [];
        do {
            promotionItems = await this.env.services.rpc({
                model: 'pos.session',
                method: 'get_pos_ui_promotion_price_list_item_by_params',
                args: [odoo.pos_session_id, {
                    offset: page * 10000,
                    limit: 10000,
                }],
            }, { shadow: true });

            this._loadPromotionPriceListItem(promotionItems);
            page += 1;
            if (this.get_order() && promotionItems.length > 0) {
                this.get_order().assign_pricelist_item_to_orderline();
            };
        } while(promotionItems.length > 0);
        if (this.get_order()) {
            this.get_order().autoApplyPriceListProgram();
        };
    }

    _loadPromotionPriceListItem(promotionItems) {
        for (let item of promotionItems) {
            let str_id = `${item.program_id[0]}p${item.id}`;
            this.pro_pricelist_item_by_id[str_id] = item;
//            self.pricelistProApplicableProducts.add(item.product_id[0]); // todo: bổ sung thêm nếu sử dụng cơ chế load CT làm giá trong background
            item.product_id = item.product_id[0];
            item.str_id = str_id;
            item.program_id = item.program_id[0];
            item.program = this.promotion_program_by_id[item.program_id];
            item.program.pricelistItems.push(item);
            item.program.productPricelistItems.add(item.product_id);
            item.display_name = item.display_name;
            let program_clone = {...item.program};
            delete program_clone.id;
            delete program_clone.str_id;
            delete program_clone.display_name;
            item = Object.assign(item, program_clone);
        };
        this.promotionPricelistItems.push(...promotionItems);
    }

    get_reward_product_ids(program) {
        // Sản phẩm thưởng phải là sản phẩm được load trên POS
        var self = this;
        return [...program.reward_product_ids].reduce((tmp, r) => {
            let product_id = self.db.get_product_by_id(r);
            if (product_id) {tmp.push(r);};
            return tmp;
        }, []);
    }

    get_valid_reward_code_promotion(program) {
        // Sản phẩm tặng phải có đơn giá nhỏ hơn sản phẩm điều kiện trong giỏ hàng có đơn giá lớn nhất
        // @return Array(product_id: int,...)
        let available_products = this.get_reward_product_ids(program);
        let valid_products_in_order = this.env.pos.get_order().get_orderlines_to_check().filter(line => program.valid_product_ids.has(line.product.id)).map(l => l.product);
        let ref_product = valid_products_in_order.sort((a,b) => b.lst_price - a.lst_price).at(0);
        let valid_rewards = available_products.filter(p => this.env.pos.db.get_product_by_id(p).lst_price < ref_product.lst_price);
        return valid_rewards
    }

    get_program_by_id(str_id) {
        str_id = String(str_id);
        if (str_id.includes('p')) {
            let [pId, itemId] = str_id.split('p');
            return this.pro_pricelist_item_by_id[str_id];
        } else {
            return this.promotion_program_by_id[str_id];
        };
    }

    getPromotionCode(program) {
        return program.codes[this.get_order().access_token]
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
        this.key_program = options.key_program || false;
        this._set_original_price(this.product.get_price(this.order.pricelist, this.get_quantity()));
    }

    export_as_JSON() {

        const result = super.export_as_JSON(...arguments);

        result.original_price = this.original_price;
        result.is_reward_line = this.is_reward_line;

        let promotion_usage_ids = [];
        this.promotion_usage_ids.forEach(_.bind( function(item) {
            return promotion_usage_ids.push([0, 0, item]);
        }, this));
        result.promotion_usage_ids = promotion_usage_ids;
        result.pricelist_item = this.pricelist_item ? this.pricelist_item.str_id : null;
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
                    item.str_id,
                    item.promotion_type,
                    item.discount_based_on,
                ));
            }
        };
        this.is_reward_line = json.is_reward_line;
        this.pricelist_item = json.pricelist_item ? this.pos.pro_pricelist_item_by_id[json.pricelist_item] : null;
        super.init_from_JSON(...arguments);
    }

    set_point(point) {
        let old_point = this.point;
        super.set_point(point);
        if (!old_point && this.point) {
            if (this.promotion_usage_ids !== undefined && this.promotion_usage_ids.length > 0) {
                this.promotion_usage_ids = [];
                this.reset_unit_price();
                this.order._resetPromotionPrograms(false);
            };
        };
    }

    set_quantity(quantity, keep_price) {
        let result = super.set_quantity(...arguments);
        let reset = false;
        if (this.promotion_usage_ids !== undefined && this.promotion_usage_ids.length > 0 && !this.pos.no_reset_program) {
            this.promotion_usage_ids = [];
            this.reset_unit_price();
            this.order._resetPromotionPrograms(false);
            reset = true;
        };
        if (!this.pos.no_reset_program && !reset && this.order._isAppliedCartPromotion()) {
            this.order._resetCartPromotionPrograms();
        };
        // Trường hợp tạo dòng mới sau khi áp dụng CTKM không cần phải cập nhật danh sách CTKM
        if (!this.pos.no_reset_program) {
            // Trường hợp thêm sản phẩm vào đơn, ordeline này không có trong order.orderlines, cần xét thêm line_no_incl_order
            let line_no_incl_order = null;
            if (!this.order.orderlines.find(l => l.cid == this.cid)) {
                line_no_incl_order = {...this};
            };
            this.order._updateActivatedPromotionPrograms(line_no_incl_order);
            if (!this.is_not_create) {
                this.order.autoApplyPriceListProgram();
            };
        }
        return result;
    }

    clone() {
        var orderline = super.clone();
        orderline.promotion_usage_ids = [...this.promotion_usage_ids];
        return orderline;
    }

    // Overwrite method of base model
    // add_product >> create orderLine >> set_quantity >> create orderLine >> set_orderline_options >> can_be_merged_with() >> add_orderline >> add_product
    can_be_merged_with(orderline) {
        let self = this;
        function _check_pro() {
            if (!(self.promotion_usage_ids || orderline.promotion_usage_ids) && (self.promotion_usage_ids != orderline.promotion_usage_ids)) {return false;};
            if (self.promotion_usage_ids.length !== orderline.promotion_usage_ids.length) {return false;};
            for (let usage1 of self.promotion_usage_ids) {
                if (orderline.promotion_usage_ids.some(u => !(u.discount_amount == usage1.discount_amount && u.str_id == usage1.str_id))) {return false;}
            };
            return true;
        };
        var price = parseFloat(round_di(this.price || 0, this.pos.dp['Product Price']).toFixed(this.pos.dp['Product Price']));
        var order_line_price = orderline.get_product().get_price(orderline.order.pricelist, this.get_quantity());
        order_line_price = round_di(orderline.compute_fixed_price(order_line_price), this.pos.currency.decimal_places);
        if (!utils.float_is_zero(price - orderline.price, this.pos.currency.decimal_places)) {
            return false;
        } else if (!_check_pro()) {
            return false;
        } else if (this.get_product().id !== orderline.get_product().id) {
            return false;
        } else if (!this.get_unit() || !this.get_unit().is_pos_groupable) {
            return false;
        } else if (this.get_discount() > 0) {
            return false;
        } else if (!utils.float_is_zero(price - order_line_price - orderline.get_price_extra(), this.pos.currency.decimal_places) && !this.is_applied_promotion() && !order_line.is_applied_promotion()) {
            return false;
        } else if (this.product.tracking == 'lot' && (this.pos.picking_type.use_create_lots || this.pos.picking_type.use_existing_lots)) {
            return false;
        } else if (this.description !== orderline.description) {
            return false;
        } else if (orderline.get_customer_note() !== this.get_customer_note()) {
            return false;
        } else if (this.refunded_orderline_id) {
            return false;
        } else {
            return true;
        }
    }

    get_original_price() {
        return this.product.get_display_price(this.order.pricelist, 1)
    }

    _set_original_price(price){
        this.order.assert_editable();
        var parsed_price = !isNaN(price) ?
            price :
            isNaN(parseFloat(price)) ? 0 : field_utils.parse.float('' + price);
        this.original_price = round_di(parsed_price || 0, this.pos.dp['Product Price']);
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
        } else if (!(this.promotion_usage_ids.length > 0)) {
            result = false;
        }
        return result;

    }

    get_applied_promotion_str() {
        let result = [];
        if (!this.promotion_usage_ids) {
            return [];
        };
        for (const usage of this.promotion_usage_ids) {
            let pro = this.pos.get_program_by_id(usage.str_id);
            result.push({
                id: usage.program_id,
                str: pro.name,
                code: this.pos.getPromotionCode(pro),
                discount_amount: this.quantity * usage.discount_amount
            });
        };
        return result;
    }

    isValidCartCondProduct(program) {
        return (!this.is_reward_line
                && program.valid_product_ids.has(this.product.id)
                && (program.is_original_price ? !this.get_total_discounted() : true))
    };
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
        json.validOnOrderPricelistItem = this.validOnOrderPricelistItem || [];
        json.activatedInputCodes = this.activatedInputCodes;
        json.reward_voucher_program_id = this.reward_voucher_program_id || null;
        json.cart_promotion_program_id = this.cart_promotion_program_id || null;
        json.reward_for_referring = this.reward_for_referring || null;
        json.referred_code_id = this.referred_code_id || null;
        json.surprise_reward_program_id = this.surprise_reward_program_id || null;
        json.buy_voucher_get_code_rewards = this.buy_voucher_get_code_rewards || [];
        json.surprising_reward_line_id = this.surprising_reward_line_id || null;
        return json;
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.activatedComboPrograms = new Set(json.activatedComboPrograms);
        this.activatedCodePrograms = new Set(json.activatedCodePrograms);
        this.activatedPricelistItem = new Set(json.activatedPricelistItem);
        this.validOnOrderPricelistItem = json.validOnOrderPricelistItem || [];
        this.activatedInputCodes = json.activatedInputCodes;
        this.get_history_program_usages();
        this.historyProgramUsages = this.historyProgramUsages != undefined ? this.historyProgramUsages : {all_usage_promotions: {}};
        this.reward_voucher_program_id = json.reward_promotion_voucher_id;
        this.cart_promotion_program_id = json.cart_promotion_program_id || null;
        this.reward_for_referring = json.reward_for_referring || null;
        this.referred_code_id = json.referred_code_id || null;
        this.surprise_reward_program_id = json.surprise_reward_program_id || null;
        this.buy_voucher_get_code_rewards = json.buy_voucher_get_code_rewards || [];
        this.surprising_reward_line_id = json.surprising_reward_line_id || null;
        if (this.partner) {
            this.set_partner(this.partner);
        };
    }
    /**
     * @override
     */
    async set_partner(partner) {
        const oldPartner = this.get_partner();
        super.set_partner(partner);
        if (oldPartner !== this.get_partner()) {
            await this.get_history_program_usages();
            await this.update_surprising_program();
        };
        await this.load_promotion_valid_new_partner();
        // Đặt lại và gán pricelist_item vào các order_line
        this.assign_pricelist_item_to_orderline()
        this.activatedInputCodes = [];
        this._resetPromotionPrograms();
        this._resetCartPromotionPrograms();
        this.autoApplyPriceListProgram();
    }

    // New method
    async load_promotion_valid_new_partner() {
        const partner = this.get_partner();
        let proPrograms = Object.keys(this.pos.promotion_program_by_id);
        if (partner) {
            let promotionValidPartners = await this.pos.env.services.rpc({
                    model: 'pos.config',
                    method: 'load_promotion_valid_new_partner',
                    args: [[this.pos.config.id], [partner.id], proPrograms],
            });
            promotionValidPartners = promotionValidPartners || [];
            for (let program_id of proPrograms){
                    let validProgram = this.pos.promotionPrograms.find(p => p.id == program_id);
                if (promotionValidPartners.includes(program_id)) {
                    if (validProgram) {
                        validProgram.valid_customer_ids.add(partner.id);
                    };
                } else {
                    validProgram.valid_customer_ids.delete(partner.id);
                };
            };
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
            self.historyProgramUsages = result || {all_usage_promotions: {}};
        });
    }

    async update_surprising_program() {
        var self = this;
        const customer = this.get_partner();
        let surprisingLines = this.pos.surprisingRewardProducts.map(l => l.id);
        if (surprisingLines.length > 0) {
            await this.pos.env.services.rpc({
                model: 'pos.config',
                method: 'update_surprising_program',
                args: [
                    [this.pos.config.id],
                    surprisingLines
                ],
                kwargs: { context: session.user_context },
            }).then((result) => {
                for (let [line_id, issued_qty] of Object.entries(result)) {
                    let line = this.pos.surprisingRewardProducts.find(r=>r.id == line_id);
                    line.issued_qty = issued_qty;
                };
            });
        };
    }

    _programIsApplicableAutomatically(program) {

        if (program.with_code) {
            if (this.activatedInputCodes) {
                if (!this.activatedInputCodes.map(code => code.program_id).includes(program.program_id)) {return false;};
            } else {return false;};
        };
        const customer = this.partner;
        if (!program.valid_customer_ids.has(customer ? customer.id : 0)) {return false;};
        const now = new Date(new Date().toLocaleString('en', {timeZone: 'UTC'}))
        if (program.to_date && program.to_date <= now) {
            return false;
        };
        if (program.from_date && program.from_date >= now) {
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
        let priceItem;
        if (!this._products_in_order().has(product.id)) {
            priceItem = this._getPricelistItem(product);
        }
        else {
            priceItem = this.validOnOrderPricelistItem.find(item => {return this.pos.pro_pricelist_item_by_id[item].product_id == product.id});
            priceItem = this.pos.pro_pricelist_item_by_id[priceItem];
        };
        if (priceItem) {
            options['pricelist_item'] = priceItem;
            if (priceItem.str_id && !this.validOnOrderPricelistItem.includes(priceItem.str_id)) {
                this.validOnOrderPricelistItem.push(priceItem.str_id);
            };
        };
        super.add_product(product, options);
    }

    set_orderline_options(line, options) {
        super.set_orderline_options(...arguments);
        if (options && options.is_reward_line) {
            line.price_manually_set = true;
        }
        line.promotion_usage_ids = options.promotion_usage_ids || [];
        line.is_cart_discounted = options.is_cart_discounted || false;
        line.is_reward_line = options.is_reward_line || false;
        line.is_new_line = options.is_new_line || false;
        line.selectedReward = options.selectedReward || false;
        line.is_not_create = options.is_not_create || false;
        line.pricelist_item = options.pricelist_item || false;
        if (!line.order.orderlines.find(l => l.cid == line.cid)) {
            line.order.autoApplyPriceListProgram(line);
        };
    }

    async _initializePromotionPrograms(v) {
        if (!this.activatedCodePrograms) {
            this.activatedCodePrograms = new Set();
        };
        if (!this.activatedComboPrograms) {
            this.activatedComboPrograms = new Set();
        };
        if (!this.activatedPricelistItem) {
            this.activatedPricelistItem = new Set();
        };
        if (!this.validOnOrderPricelistItem) {
            this.validOnOrderPricelistItem = [];
        };
        if (!this.activatedInputCodes) {
            this.activatedInputCodes = [];
        };
    }

    _resetPromotionPrograms(resetActivatedPrograms=true) {
        if (resetActivatedPrograms) {
//            this.activatedInputCodes = [];
            this.activatedComboPrograms = new Set();
            this.activatedCodePrograms = new Set();
            this.activatedPricelistItem = new Set();
        }
        this.reward_for_referring = null;
        this.referred_code_id = null;
        this.surprise_reward_program_id = null;
        this.buy_voucher_get_code_rewards = [];
        this.surprising_reward_line_id = null;
        this._get_reward_lines().forEach(reward_line => {
//            this.orderlines.remove(reward_line);
            reward_line.is_reward_line = false;
            reward_line.reset_unit_price()
        });
//        this.remove_orderline(this._get_reward_lines()); // TODO: Xác định reward line của CTKM nào
        let orderlines = this.orderlines.filter(line => line._isDiscountedComboProgram() || line.promotion_usage_ids)
        orderlines.forEach(line => line.reset_unit_price());
        orderlines.forEach(line => line.promotion_usage_ids = []);
        this.pos.promotionPrograms.forEach(p => {
            p.reward_for_referring = false;
        });
        this._updateActivatedPromotionPrograms();
    }

    _get_reward_lines_of_cart_pro() {
        const orderLines = super.get_orderlines(...arguments);
        if (orderLines) {
            return orderLines.filter((line) => line.is_reward_line && line.is_cart_discounted);
        }
        return orderLines;
    }

    _isAppliedCartPromotion() {
        for (let line of this.get_orderlines_to_check()) {
            if (line.promotion_usage_ids.some(usage => this.pos.get_program_by_id(usage.str_id).promotion_type == 'cart')) {
                return true;
            };
            if (this.reward_voucher_program_id || this.cart_promotion_program_id) {
                return true;
            };
        };
        return false;
    }

    _resetCartPromotionPrograms() {
        let to_remove_lines = this._get_reward_lines_of_cart_pro();
        let has_cart_program = to_remove_lines.length > 0 || this.reward_voucher_program_id || this.cart_promotion_program_id;
        for (let line of to_remove_lines) {
//            this.remove_orderline(line);
            line.is_reward_line = false;
            line.reset_unit_price();
        };
        this.reward_voucher_program_id = null;
        this.cart_promotion_program_id = null;
        // TODO: Xác định reward line của CTKM nào
        let orderlines = this.orderlines.filter(line => line.is_cart_discounted);
        orderlines.forEach(line => line.reset_unit_price());
        orderlines.forEach(line => line.promotion_usage_ids = []);
        orderlines.forEach(line => line.is_cart_discounted = false);
        this._updateActivatedPromotionPrograms();
        if (has_cart_program) {
            Gui.showNotification(_.str.sprintf(`Chương trình Hóa đơn đã được đặt lại!`), 2000);
        };
    }

    _get_to_check_programs(){
        let result = this.pos.promotionPrograms.filter(p=> p.promotion_type != 'pricelist');
        if (this.validOnOrderPricelistItem) {
            let priceItems = this.validOnOrderPricelistItem.map(proID => this.pos.pro_pricelist_item_by_id[proID]);
            result.concat(priceItems.filter(item => item));
        };
        return result;
    }

    async _updateActivatedPromotionPrograms(line_no_incl_order) {
        this.activatedComboPrograms = new Set();
        this.activatedCodePrograms = new Set();
        this.activatedPricelistItem = new Set();
        let to_check = this._get_to_check_programs();
        let validPromotionPrograms = this.verifyProgramOnOrder(to_check, line_no_incl_order);
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
//        result.push(...Array.from(this.activatedPricelistItem).map(proID => this.pos.pro_pricelist_item_by_id[proID]));
        if (this.validOnOrderPricelistItem) {
            let products = new Set(this.get_orderlines_to_check().filter(l=>l.quantity > 0).map(l => l.product.id));
            let validPricelistItems = this.validOnOrderPricelistItem.filter(str_id => {
                    let pro = this.pos.pro_pricelist_item_by_id[str_id];
                    return pro && products.has(pro.product_id)
                }
            );
            result.push(...validPricelistItems.map(proID => this.pos.pro_pricelist_item_by_id[proID]).filter(pl => pl));
        };
        return result;
    }

    getPotentialProgramsToSelect() {
        let toCheck = this.getActivatedPrograms();
        // todo: Có thể đặt method _updateActivatedPro, thay cho method bên dưới, lưu kết quả của method này trên Object Order
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

    _products_in_order() {
        return new Set(this.get_orderlines().map(l => l.product.id));
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
                is_new_line: l.is_new_line,
                price: l.price,
                full_product_name: l.full_product_name,
                tax_ids: [...(l.tax_ids || [])],
                selectedReward: l.selectedReward,
                discount: l.discount,
                point: l.point,
                is_product_defective: l.is_product_defective
            });
        })
        return lines;
    }

    get_orderlines_to_check() {
        return this.get_orderlines().filter(line => {
            if (line.is_reward_line || line.point || line.is_product_defective || line.discount) {
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

    _filterToApplyPro(ols) {
        return ols.filter(line => {
            if (line.is_reward_line || line.point || line.is_product_defective || line.discount) {
                return false;
            };
            return true;
        });
    }


    _get_program_usage_ids() {
        let lines = this.get_orderlines().filter(line => line.is_applied_promotion());
        return lines.reduce((acc, line) => {
        acc.push(...line.promotion_usage_ids); return acc;}, []);
    }

    assign_pricelist_item_to_orderline() {
//        this.validOnOrderPricelistItem = [];
        for (let line of this.get_orderlines()) {
            if (!line.pricelist_item) {
                let priceItem = this._getPricelistItem(line.product);
                if (priceItem) {
                    line.pricelist_item = priceItem;
                    if (priceItem.str_id && !this.validOnOrderPricelistItem.includes(priceItem.str_id)) {
                        this.validOnOrderPricelistItem.push(priceItem.str_id);
                    };
                };
            } else if (line.pricelist_item && !this.validOnOrderPricelistItem.includes(line.pricelist_item.str_id)) {
                this.validOnOrderPricelistItem.push(line.pricelist_item.str_id);
            };
        };
    }

    validate_code_pricelist(pro) {
        for (let line of this.get_orderlines()) {
            let priceItem = this._getPricelistItem(line.product, true);
            if (priceItem && !this.validOnOrderPricelistItem.includes(priceItem.str_id)) {
                this.validOnOrderPricelistItem.push(priceItem.str_id);
            };
        };
    }

    _getPricelistItem(product, check_with_code=false) {
        let programs = this.pos.promotionPrograms.filter(p => p.promotion_type == 'pricelist' && (check_with_code ? p.with_code : !p.with_code));
        let pricelistItem;
        for (let program of programs) {
            pricelistItem = program.pricelistItems.find(item => item.product_id === product.id);
            if (pricelistItem && this._programIsApplicableAutomatically(pricelistItem.program)) {
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
                if (['combo', 'code', 'cart', 'pricelist'].includes(this.pos.promotion_program_by_id[usage.program_id].promotion_type)){
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
            v = v/ (program.qty_per_combo || 1);
            result[k] = v;
        });
        return result
    }

    // Filter based on promotion_usage_ids
    _filterOrderLinesToCheckComboPro(order_lines) {
        return order_lines.filter(l=>!l.is_reward_line && l.quantity > 0).filter(l => {
            for (let usage of l.promotion_usage_ids) {
                let program = this.pos.get_program_by_id(usage.str_id);
                if (['pricelist', 'combo', 'code'].includes(program.promotion_type)) {return false};
//                if (program.promotion_type == 'code' && program.discount_based_on == 'unit_price' && usage.disc_amount) {return false};
            };
            return true;
        });
    }

    _filterOrderLinesToCheckCodePro(pro, order_lines) {
        if (pro.promotion_type == 'code' && pro.discount_based_on == 'unit_price') {
            return order_lines.filter(line => line.quantity > 0).filter(function(l) {
                return !(l.promotion_usage_ids && l.promotion_usage_ids.length) ? true : false;
            });
        } else if (pro.promotion_type == 'code' && pro.discount_based_on == 'discounted_price') {
            return order_lines.filter(line => line.quantity > 0).filter(function(l) {
                if (l.promotion_usage_ids && l.promotion_usage_ids.length) {
                    if (l.price == 0 || l.is_reward_line) {return false}
                    if (l.promotion_usage_ids.some(p => p.str_id == pro.str_id)) {return false}
                    else {return true};
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

    prepare_to_discount_line_val(line, quantity, price_unit, is_not_discount) {
        return {
            product: line.product,
            quantity: quantity,
            price: price_unit == undefined ? line.price : price_unit,
            isNew: true,
            is_new_line: line.is_new_line,
            pricelist_item: line.pricelist_item,
            selectedReward: line.selectedReward,
            promotion_usage_ids: [...line.promotion_usage_ids],
            refunded_orderline_id: line.refunded_orderline_id,
            is_not_discount: is_not_discount
        }
    }

    _checkNumberOfCode(codeProgram, order_lines, to_discount_line_vals , count, max_count = false, to_apply_lines = {}) {
        let to_check_order_lines = this._filterOrderLinesToCheckCodePro(codeProgram, order_lines);
        to_check_order_lines.sort((a, b) => a.cid.localeCompare(b.cid));
        count = count || 0;
        to_discount_line_vals = to_discount_line_vals || [];
        let result = [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count];
        var valid_product_ids = codeProgram.valid_product_ids;

//        if (codeProgram.reward_type == "code_amount") {
//            max_count = 1;
//        }
        // todo: consider to sort by 'lst_price' ASC for type code_buy_x_get_cheapest
        to_check_order_lines.sort((a,b) => (a.product.lst_price < b.product.lst_price) ? 1 : ((b.product.lst_price < a.product.lst_price) ? -1 : 0))
        var oneCombo = [];
        var decimals = this.pos.dp['Product Unit of Measure'];
        let min_quantity = codeProgram.min_quantity;
        const funct_check_q = function(p, {product, quantity}){
            if (!valid_product_ids.size || valid_product_ids.has(product.id)) { return p + quantity; }
            return p;
        }
        var check_q = 0;
        if (to_check_order_lines.length) {
            check_q = to_check_order_lines.reduce(funct_check_q, 0);
        }
        var number_product_apply = 0;
        if (codeProgram.reward_type == "code_amount" && ((codeProgram.discount_apply_on == "order" && check_q >= valid_product_ids.size) || !valid_product_ids.size)) {
            for (const ol of to_check_order_lines.filter(ol => valid_product_ids.has(ol.product.id) || !valid_product_ids.size).sort((a, b) => a.cid.localeCompare(b.cid))) {
                var ol_quantity = ol.quantity;
                number_product_apply += ol_quantity
                if (codeProgram.reward_quantity && number_product_apply >= codeProgram.reward_quantity) {
                    ol_quantity = codeProgram.reward_quantity - number_product_apply + ol_quantity;
                    number_product_apply = codeProgram.reward_quantity;
                }

                if (ol.quantity - ol_quantity) {
                    to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, ol.quantity - ol_quantity, ol.price, true));
                }

                to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, ol_quantity, ol.price));
                ol.quantity = 0;
                ol.quantityStr = field_utils.format.float(ol.quantity, {digits: [69, decimals]});
                if (ol.key_program && to_apply_lines[ol.key_program]) {
                    for (let new_line of to_apply_lines[ol.key_program].filter((l)=>l.product.id === ol.product.id)) {
                        new_line.quantity = ol.quantity;
                    }
                }
            }
            var total_price = to_discount_line_vals.reduce((p, {price, quantity}) => p + price*quantity, 0)
            for (const discount_line_val of to_discount_line_vals) {
                discount_line_val.total_price = total_price;
            }
            return [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, 1, to_apply_lines];
        }
        for (const ol of to_check_order_lines.filter(ol => !valid_product_ids.size || (valid_product_ids.has(ol.product.id)  && ol.quantity >= codeProgram.min_quantity)).sort((a, b) => a.cid.localeCompare(b.cid))) {
            var quantity_combo = Math.floor(ol.quantity / min_quantity)
            if (max_count && count + quantity_combo >= max_count){
                quantity_combo = max_count - count
            }
            for (var i =0; i<quantity_combo; i++) {
                var ol_quantity = min_quantity;
                number_product_apply += ol_quantity;
                if (codeProgram.reward_quantity && number_product_apply >= codeProgram.reward_quantity) {
                    ol_quantity = codeProgram.reward_quantity - number_product_apply + ol_quantity;
                    number_product_apply = codeProgram.reward_quantity;
                }


                if (min_quantity - ol_quantity) {
                    to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, min_quantity - ol_quantity, ol.price, true));
                }

                to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, ol_quantity, ol.price));
                ol.quantity -= min_quantity;
            }
            ol.quantityStr = field_utils.format.float(ol.quantity, {digits: [69, decimals]});
            count += quantity_combo;
            if (ol.key_program && to_apply_lines[ol.key_program]) {
                for (let new_line of to_apply_lines[ol.key_program].filter((l)=>l.product.id === ol.product.id)) {
                    new_line.quantity = ol.quantity;
                }
            }
        }

        if (max_count && count >= max_count) {
            var total_price = to_discount_line_vals.reduce((p, {price, quantity}) => p + price*quantity, 0)
            for (const discount_line_val of to_discount_line_vals) {
                discount_line_val.total_price = total_price;
            }
            return [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count, to_apply_lines];
        }

        var order_lines_has_valid_product = to_check_order_lines.filter(l => !valid_product_ids.size || valid_product_ids.has(l.product.id)).sort((a, b) => a.cid.localeCompare(b.cid));

        var oneCombo = [];
        var total_quantity = order_lines_has_valid_product.reduce((q, {quantity}) => q + quantity, 0);
        if (total_quantity >= codeProgram.min_quantity) {
            var oddComboNumber = (total_quantity-(total_quantity%codeProgram.min_quantity))/codeProgram.min_quantity;
            var min_quantity_tmp = oddComboNumber*codeProgram.min_quantity;
            for (const ol of order_lines_has_valid_product) {
                if (ol.quantity <= min_quantity_tmp) {
                    var quantity = ol.quantity;
                    min_quantity_tmp -= ol.quantity;
                    total_quantity -= ol.quantity;
                    number_product_apply += quantity;
                    if (codeProgram.reward_quantity && number_product_apply >= codeProgram.reward_quantity) {
                        quantity = codeProgram.reward_quantity - number_product_apply + quantity;
                        number_product_apply = codeProgram.reward_quantity;
                    }

                    if (ol.quantity - quantity) {
                        to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, ol.quantity - quantity, ol.price, true));
                    }
                    to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, quantity, ol.price));
                    ol.quantity = 0;
                    ol.quantityStr = field_utils.format.float(ol.quantity, {digits: [69, decimals]});
                    if (ol.key_program && to_apply_lines[ol.key_program]) {
                        for (let new_line of to_apply_lines[ol.key_program].filter((l)=>l.product.id === ol.product.id)) {
                            new_line.quantity = ol.quantity;
                        }
                    }
                }
            }
            count += oddComboNumber;
        }

        if (codeProgram.reward_type == "code_percent" && codeProgram.discount_apply_on == "order" && count > 0) {
            for (const ol of to_check_order_lines.filter(ol => valid_product_ids.has(ol.product.id)).sort((a, b) => a.cid.localeCompare(b.cid))) {
                var ol_quantity = ol.quantity;
                number_product_apply += ol_quantity;
                if (codeProgram.reward_quantity && number_product_apply >= codeProgram.reward_quantity) {
                    ol_quantity = codeProgram.reward_quantity - number_product_apply + ol_quantity;
                    number_product_apply = codeProgram.reward_quantity;
                }

                if (ol.quantity - ol_quantity) {
                    to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, ol.quantity - ol_quantity, ol.price, true));
                }

                to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, ol_quantity, ol.price));
                ol.quantity = 0;
                ol.quantityStr = field_utils.format.float(ol.quantity, {digits: [69, decimals]});
                if (ol.key_program && to_apply_lines[ol.key_program]) {
                    for (let new_line of to_apply_lines[ol.key_program].filter((l)=>l.product.id === ol.product.id)) {
                        new_line.quantity = ol.quantity;
                    }
                }
            }
        }

        var map_to_discount_line_vals = {};

        for (const to_discount_line_val of to_discount_line_vals) {
            var key = to_discount_line_val.product.id + '-' + to_discount_line_val.promotion_usage_ids.reduce((p, {str_id}) => p + '-' + str_id, '') + '-' + to_discount_line_val.is_not_discount;
            if (map_to_discount_line_vals[key]) {
                map_to_discount_line_vals[key].quantity += to_discount_line_val.quantity;
            } else {
                map_to_discount_line_vals[key] = to_discount_line_val;
            }
        }

        to_discount_line_vals = Object.values(map_to_discount_line_vals);

        var total_price = to_discount_line_vals.reduce((p, {price, quantity}) => p + price*quantity, 0)
        for (const discount_line_val of to_discount_line_vals) {
            discount_line_val.total_price = total_price;
        }
        if (codeProgram.reward_type == "code_buy_x_get_y" && count > 0) {
            let reward_products = new Set(this.pos.get_valid_reward_code_promotion(codeProgram));
            let to_take_on_reward_qty = count * codeProgram.reward_quantity;
            let reward_qty_taken = 0;
            let able_be_reward_ols = order_lines.filter(ol=> ol.quantity > 0)
                                                .filter(ol => reward_products.has(ol.product.id) && ol.price > 0).sort((a, b) => a.cid.localeCompare(b.cid));
            for (const ol of able_be_reward_ols) {
                let taken_reward_qty = Math.min(ol.quantity, to_take_on_reward_qty);
                ol.quantity = ol.quantity - taken_reward_qty;
                let reward_line = this.prepare_to_discount_line_val(ol, taken_reward_qty, ol.price);
                reward_line['is_reward_line'] = true;
                to_discount_line_vals.push(reward_line);
                ol.quantityStr = field_utils.format.float(ol.quantity, {digits: [69, decimals]});
                to_take_on_reward_qty -= taken_reward_qty;
                if (ol.key_program && to_apply_lines[ol.key_program]) {
                    for (let new_line of to_apply_lines[ol.key_program].filter((l)=>l.product.id === ol.product.id)) {
                        new_line.quantity = ol.quantity;
                    }
                }
                if (to_take_on_reward_qty <= 0.0) {break;};
            };
        };
        return [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count, to_apply_lines];
    }

    /*
    * recursion function
    * return {number} count of  combo
    */
    _checkNumberOfCombo(comboProgram, order_lines, to_discount_line_vals , count, only_count=false, limit_qty=0) {
        if (only_count) {
            order_lines = order_lines.map(obj => ({...obj}));
        };
        let to_check_order_lines = this._filterOrderLinesToCheckComboPro(order_lines);
        count = count || 0;
        to_discount_line_vals = to_discount_line_vals || [];
        let result = [to_check_order_lines.filter((l)=>l.quantity > 0.0), to_discount_line_vals, count];

        // Check limit_qty: chỉ lấy đúng số lượng combo cần thiết để giảm giá
        if (limit_qty && count >= limit_qty) {
            return result;
        }

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
        // Check if there is a limitation of number of combo applied program per program
        if (comboProgram.limit_usage_per_program && this.historyProgramUsages) {
            let historyUsed = (this.historyProgramUsages.all_usage_promotions || {})[comboProgram.id] || 0;
            let applied_per_program = historyUsed + (this._getNumberOfComboApplied()[comboProgram.id] || 0.0) + count;
            if  (applied_per_program >= comboProgram.max_usage_per_program) {
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
                    oneCombo.push(this.prepare_to_discount_line_val(ol, qty_taken_on_candidate, ol.price));
                    qty_to_take_on_candidates -= qty_taken_on_candidate;
                    if (qty_to_take_on_candidates <= 0.0) {break;};
                };
            };
            to_discount_line_vals.push(oneCombo);
            return this._checkNumberOfCombo(comboProgram, order_lines, to_discount_line_vals, count + 1, only_count, limit_qty);
        };
    }

    _checkQtyOfProductForPricelist(pricelistItem, orderLines, programIsVerified, to_apply_lines) {
        let to_check_order_lines = this._filterOrderLinesToCheckPricelistPro(pricelistItem, orderLines);
        let qty = 0.0;
        let to_discount_line_vals = [];
        let max_reward_qty = 0;
        if (pricelistItem.reward_quantity > 0 && pricelistItem.with_code == true) {
            let applied_this_order = (this._getNumberOfComboApplied()[pricelistItem.program_id] || 0.0);
            max_reward_qty = pricelistItem.reward_quantity - applied_this_order;
            if (programIsVerified) {
                let appliedOthers = Object.entries(programIsVerified).filter(([pro_str_id, count]) => {
                    let [pId, itemId] = pro_str_id.split('p');
                    return pId == pricelistItem.program_id
                });
                if (appliedOthers.length > 0) {
                    max_reward_qty -= appliedOthers.reduce((tmp, el) => tmp + el[1], 0);
                };
            };
            if (to_apply_lines) {
                let appliedOthers = Object.entries(to_apply_lines).filter(([pro_str_id, line_vals]) => {
                    let [pId, itemId] = pro_str_id.split('p');
                    return pId == pricelistItem.program_id;
                });
                if (appliedOthers) {
                    let appliedQty = appliedOthers.reduce((sum, appliedOther) => sum + appliedOther[1].reduce((tmp, l)=>tmp + l.quantity, 0), 0);
                    max_reward_qty -= appliedQty;
                };
            };


        };
        for (let line of to_check_order_lines) {
            if (line.quantity > 0) {
                // CT Làm giá sử dụng code được thiết lập SL giảm tối đa
                if (max_reward_qty) {
                    let qty_taken = Math.min(max_reward_qty, line.quantity);
                    qty += qty_taken;
                    to_discount_line_vals.push(this.prepare_to_discount_line_val(line, qty_taken, line.product.lst_price));
                    line.quantity -= qty_taken;
                    max_reward_qty -= qty_taken;
                    if (max_reward_qty <= 0.0) break;
                }
                // CT Làm giá
                else if (!pricelistItem.with_code) {
                    qty += line.quantity;
                    to_discount_line_vals.push(this.prepare_to_discount_line_val(line, line.quantity, line.product.lst_price));
                    line.quantity = 0;
                };
            };
        };
        return [orderLines, to_discount_line_vals, qty]
    }

    _validateLimitUsagePromotion() {
        let applied_combo_pros = this._getNumberOfComboApplied();
        for (let [program_id, applied_qty_on_order] of Object.entries(applied_combo_pros)) {
            let program = this.pos.get_program_by_id(program_id);
            if (program.promotion_type=='combo' && program.limit_usage_per_order) {
                if  (applied_qty_on_order > program.max_usage_per_order) {
                    return [program, 'limit_usage_per_order', program.max_usage_per_order];
                };
            };
            if (program.promotion_type=='combo' && program.limit_usage_per_customer) {
                let historyUsed = (this.historyProgramUsages || {})[program.id] || 0;
                let applied_per_customer = historyUsed + applied_qty_on_order;
                if  (applied_per_customer > program.max_usage_per_customer) {
                    return [program, 'limit_usage_per_customer', program.max_usage_per_customer - historyUsed];
                };
            };
            if (program.promotion_type=='combo' && program.limit_usage_per_program) {
                let historyUsed = (this.historyProgramUsages.all_usage_promotions || {})[program.id] || 0;
                let applied_per_program = historyUsed + applied_qty_on_order;
                if  (applied_per_program > program.max_usage_per_program) {
                    return [program, 'limit_usage_per_program', program.max_usage_per_program - historyUsed];
                };
            };
            if (['code', 'cart', 'pricelist'].includes(program.promotion_type) && program.limit_usage_per_customer) {
                let historyUsed = (this.historyProgramUsages || {})[program.id] || 0;
                if  (historyUsed >= program.max_usage_per_customer) {
                    return [program, 'limit_usage_per_customer', program.max_usage_per_customer - historyUsed];
                };
            };
            if (['code', 'cart', 'pricelist'].includes(program.promotion_type) && program.limit_usage_per_program) {
                let historyUsed = (this.historyProgramUsages.all_usage_promotions || {})[program.id] || 0;
                if  (historyUsed >= program.max_usage_per_program) {
                    return [program, 'limit_usage_per_program', program.max_usage_per_program - historyUsed];
                };
            };
        };
        return false;
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
        if (programs.length > 6) {
            return [];
        };
        let programs_combines = this.permutator(programs);
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
    verifyProgramOnOrder(toVerifyPromotionPrograms, line_no_incl_order) {
        var comboProgramToCheck = new Set();
        var programIsVerified = new Object();
        for (const program of toVerifyPromotionPrograms) {
            if (this._programIsApplicableAutomatically(program) && program.promotion_type != 'cart') {
                comboProgramToCheck.add(program);
            };
        };
        for (const program of comboProgramToCheck) {
            let to_check_order_lines = this.get_orderlines_to_check().map(obj => ({...obj}));
            if (line_no_incl_order) {
                line_no_incl_order.promotion_usage_ids = [];
                to_check_order_lines.push(line_no_incl_order);
            };
            if (program.promotion_type == 'combo') {
                if (this._filterOrderLinesToCheckComboPro(to_check_order_lines).length > 0) {
                    let NumberOfCombo = this._checkNumberOfCombo(program, to_check_order_lines, [] , 0)[2];
                    if (['combo_percent_by_qty', 'combo_fixed_price_by_qty'].includes(program.reward_type) && !(NumberOfCombo >= program.qty_min_required)) {
                        continue;
                    };
                    let reward_lines = this._get_discount_product_line_for_combo(program, NumberOfCombo, to_check_order_lines);
                    if (NumberOfCombo >= 1) {
                        programIsVerified[program.str_id] = NumberOfCombo;
                    };
                };

            }
            else if (program.promotion_type == 'code') {
                // todo: check if suitable order_line exist before check number of product
                let NumberOfCombo = this._checkNumberOfCode(program, to_check_order_lines, [] , 0)[2];
                if (NumberOfCombo >= 1) {
                    programIsVerified[program.id] = NumberOfCombo;
                };
            }
            else if (program.promotion_type == 'pricelist') {
                const inOrderProductsList = new Set(this.get_orderlines_to_check()
                            .filter(l => l.quantity > 0)
                            .filter(l => !l.promotion_usage_ids || l.promotion_usage_ids.length == 0 ? true : false)
                            .reduce((tmp, line) => {tmp.push(line.product.id); return tmp;}, []));
                if (inOrderProductsList.size) {
                    if (inOrderProductsList.has(program.product_id)) {
                        let QtyOfProduct = this._checkQtyOfProductForPricelist(program, to_check_order_lines, programIsVerified)[2];
                        if (QtyOfProduct > 0) {
                            programIsVerified[program.str_id] = QtyOfProduct;
                        };
                    };
                };
            };
        };
        return programIsVerified;
    }

    _get_discount_product_line_for_combo(program, number_of_combo, order_lines) {
        let to_discount_line_vals = [];
        let to_check_order_lines = this._filterOrderLinesToCheckComboPro(order_lines);
        let max_reward_qty = (program.reward_quantity || 1) * number_of_combo;
        let qty_to_take = max_reward_qty;
        for (const ol of to_check_order_lines.filter(ol => program.discount_product_ids.has(ol.product.id)  && ol.quantity > 0)) {
            let qty_taken = Math.min(qty_to_take, ol.quantity);
            ol.quantity = ol.quantity - qty_taken;
            to_discount_line_vals.push(this.prepare_to_discount_line_val(ol, qty_taken, ol.price));
            qty_to_take -= qty_taken;
            if (qty_to_take <= 0.0) {break;};
        };
        return to_discount_line_vals;
    }

    _apply_cart_program_to_orderline(program, to_discount_lines) {
        let code = null;
        let activatedCodeObj = this.activatedInputCodes.find(c => c.program_id === program.id)
        if (activatedCodeObj) {code = activatedCodeObj.id};
        if (program.reward_type == 'cart_get_voucher') {
            // pass
        }
        else if (program.reward_type == 'cart_discount_percent') {
            for (let line of to_discount_lines) {
                let originalPrice = line.price;
                let discAmount = round_decimals(line.price * program.disc_percent/100, this.pos.currency.decimal_places);
                if (program.disc_max_amount > 0) {
                    discAmount = discAmount < program.disc_max_amount ? discAmount : program.disc_max_amount;
                };
                let newPrice = originalPrice - discAmount;
                line.price = newPrice;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
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
                program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                line.is_cart_discounted = true;
            }
        }
        else if (program.reward_type == 'cart_discount_amount') {
            let base_total_amount = to_discount_lines.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = program.disc_amount;
            for (let line of to_discount_lines) {
                let originalPrice = line.price;
                let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, line.quantity);
                line.price = newPrice;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                line.is_cart_discounted = true;
            };
        }
        else if (program.reward_type == 'cart_get_x_free') {
            for (let line of to_discount_lines) {
                let originalPrice = line.price
                let newPrice = 0.0
                let discAmount = originalPrice - newPrice
                line.price = newPrice;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
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
            let is_reward_line = program.reward_type == 'cart_get_x_free';
            let val = this.prepare_to_discount_line_val(line, qty_taken, line.price);
            val['is_reward_line'] = is_reward_line;
            to_discount_line_vals.push(val);
        }
        return [to_discount_line_vals, orderLines]
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
            let discount_based_on_unit_price = program.discount_based_on == 'unit_price';
            let max_reward_quantity = program.reward_quantity;
            let required_order_amount_min = program.order_amount_min;
            let required_min_quantity = program.min_quantity;
            let floor = 1;
            let reward_products = program.reward_type == 'cart_get_x_free' ? program.reward_product_ids : program.discount_product_ids;
            if (!this._programIsApplicableAutomatically(program)) {
                continue
            };
            if (program.limit_usage_per_customer) {
                let historyUsed = (this.historyProgramUsages || {})[program.id] || 0;
                if  (historyUsed >= program.max_usage_per_customer) {
                    continue;
                };
            };
            if (program.limit_usage_per_program) {
                let historyUsed = ((this.historyProgramUsages || {}).all_usage_promotions || {})[program.id] || 0;
                if  (historyUsed >= program.max_usage_per_program) {
                    continue;
                };
            };

            let amountCheck;
            if (program.only_condition_product) {
                amountCheck = orderLines.filter(l=>l.isValidCartCondProduct(program))
                                        .reduce((function(sum, orderLine) {
                                            return sum + orderLine.get_price_without_tax() + orderLine.get_tax();}), 0);
                amountCheck = round_precision(amountCheck, this.pos.currency.rounding);
            } else {
                amountCheck = totalsPerProgram[program.id]['taxed'];
            };
            if (program.incl_reward_in_order_type == 'no_incl') {
                let no_incl_amount = 0;
                let no_incl_ols;
                if (program.reward_type == 'cart_get_x_free') {
                    no_incl_ols = orderLines.filter(l=>!l.get_total_discounted() && l.quantity > 0)
                                            .filter(l=>program.reward_product_ids.has(l.product.id)
                                                    // Nếu "Không bao gồm" SPKM và "Chỉ xét SPĐK", trừ SPKM có trong điều kiện
                                                    &&(program.only_condition_product ? program.valid_product_ids.has(l.product.id) : true));
                } else {
                    no_incl_ols = orderLines.filter(l=>!l.get_total_discounted() && l.quantity > 0)
                                            .filter(l=>program.discount_product_ids.has(l.product.id)
                                                    // Nếu "Không bao gồm" SPKM và "Chỉ xét SPĐK", trừ SPKM có trong điều kiện
                                                    &&(program.only_condition_product ? program.valid_product_ids.has(l.product.id) : true));
                };
                for (let ol of no_incl_ols) {
                    no_incl_amount += ol.quantity * ol.price;
                };
                amountCheck -= no_incl_amount;
            };
            if (program.order_amount_min >0 && program.order_amount_min > amountCheck) {
                continue;
            };
            let is_required_check_products = program.valid_product_ids.size > 0;
            let qty_taken = 0;
            for (const line of orderLines) {
                if (line.isValidCartCondProduct(program)) {
                    qty_taken += line.quantity;
                };
            };
            // Nếu không có sản phẩm điều kiện, Loại CT k thõa
            if (program.valid_product_ids.size > 0 && qty_taken < required_min_quantity) {
                continue;
            };

            // Tính lũy tuyến cho số lượng phần thưởng
            if (program.progressive_reward_compute) {
                if (program.order_amount_min > 0 && program.min_quantity > 0 && is_required_check_products) {
                    let amountOrderFloor = Math.floor(amountCheck/program.order_amount_min);
                    let qtyFloor = Math.floor(qty_taken /  program.min_quantity);
                    floor = Math.min(amountOrderFloor, qtyFloor);

                    max_reward_quantity         = floor * program.reward_quantity;
                    required_order_amount_min   = floor * program.order_amount_min;
                    required_min_quantity       = floor * program.min_quantity;
                } else if (program.order_amount_min > 0) {
                    floor = Math.floor(amountCheck/program.order_amount_min);
                    max_reward_quantity         = floor * program.reward_quantity;
                    required_order_amount_min   = floor * program.order_amount_min;
                } else if (program.min_quantity > 0 && is_required_check_products) {
                    floor = Math.floor(qty_taken/program.min_quantity);
                    max_reward_quantity         = floor * program.reward_quantity;
                    required_min_quantity       = floor * program.min_quantity;
                }
            }

            if (is_required_check_products && qty_taken < required_min_quantity) {
                continue;
            };
            let to_discount_lines = [];
            let to_reward_lines = [];
            let voucher_program_id = [];
            let isSelected = false;
            if (program.reward_type == 'cart_get_x_free') {
                to_reward_lines = orderLines.filter(l=>(discount_based_on_unit_price ? !l.get_total_discounted() : true) && l.quantity > 0)
                                            .filter(l=>reward_products.has(l.product.id));
            } else if (program.reward_type == 'cart_get_voucher') {
                voucher_program_id = program.voucher_program_id;
                isSelected = true;
            } else {
                to_discount_lines = orderLines.filter(l=> (discount_based_on_unit_price ? !l.get_total_discounted() : true) && l.quantity > 0)
                                              .filter(l=>reward_products.has(l.product.id));
            };
            if ((program.reward_type == 'cart_get_x_free' && to_reward_lines.length > 0)
                || (program.reward_type != 'cart_get_x_free' &&  to_discount_lines.length > 0)) {
                let reward_lines = program.reward_type == 'cart_get_x_free' ? to_reward_lines : to_discount_lines;
                let multi = floor;
                let is_valid = false;
                while (multi >= 1) {
                    let check_max_reward_quantity         = multi * program.reward_quantity;
                    let check_required_order_amount_min   = multi * program.order_amount_min;
                    let check_required_min_quantity       = multi * program.min_quantity;
                    let check_to_reward_lines = reward_lines.sort((a, b) => a.id - b.id );
                    let check_data = {};
                    for (let line of reward_lines) {
                        let taken = Math.min(line.quantity, check_max_reward_quantity);
                        check_data[line.cid] = taken;
                        check_max_reward_quantity -= taken;
                        if (check_max_reward_quantity <= 0) break;
                    };
                    let check_orderLines = this._get_clone_order_lines(this.get_orderlines_to_check());
                    let [to_apply_lines, remaining] = this.computeForListOfCartProgram(check_orderLines, {[program.str_id]: check_data});

                    let no_incl_line_total_amount = 0;
                    let discount_total = to_apply_lines[program.str_id].reduce((acc, line) => {
                        let amountPerLine;
                        if (program.incl_reward_in_order_type == 'no_incl') {
                            amountPerLine =
                                (!reward_products.has(line.product.id) && (program.only_condition_product ? program.valid_product_ids.has(line.product.id) : true))
                                ? line.promotion_usage_ids.reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0)
                                : 0.0;
                        } else if (program.incl_reward_in_order_type == 'unit_price') {
                            amountPerLine =
                                (!program.only_condition_product ? reward_products.has(line.product.id) : false)
                                ? line.promotion_usage_ids.reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0)
                                : 0.0;
                        } else {
                            amountPerLine =
                                (!program.only_condition_product || (program.only_condition_product && program.valid_product_ids.has(line.product.id)))
                                ? line.promotion_usage_ids.reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0)
                                : 0.0;
                        };
                        return acc + amountPerLine;
                    }, 0.0);
                    let amount_total_after_discount = amountCheck - discount_total;
                    let check = program.order_amount_min == 0
                                || (program.order_amount_min > 0 && check_required_order_amount_min <= amount_total_after_discount);
                    if (check) {
                        floor = multi;
                        is_valid = true;
                        break;
                    };
                    multi--;
                };
                if (!is_valid) {
                    floor = 0;
                };
            } else floor = 1;

            if (floor) {
                result.push({
                    id: program.id,
                    program: program,
                    max_reward_quantity: program.reward_quantity * floor,
                    required_order_amount_min: program.order_amount_min * floor,
                    required_min_quantity: program.min_quantity * floor,
                    amountCheck,
                    voucher_program_id,
                    to_reward_lines,
                    to_discount_lines,
                    isSelected,
                    reward_line_vals: []
                });
            };
        };
        return result
    }

    verifySurprisingProgram() {

        const inOrderProductsList = this.get_orderlines().filter(l => l.quantity > 0)
                                        .reduce((tmp, line) => {tmp.push(line.product.id); return tmp;}, []);
        let toCheckRewardLines = this.pos.surprisingRewardProducts;
        let validSurprisingPrograms = [];
        let validBuyVoucherGetCodePrograms = [];
        for (let productLine of toCheckRewardLines) {
            if (!productLine.has_check_product && !inOrderProductsList.some(product => productLine.to_check_product_ids.has(product))
                && (productLine.max_quantity > productLine.issued_qty || productLine.max_quantity <= 0)) {
                validSurprisingPrograms.push(productLine);
            };
            if (productLine.has_check_product && inOrderProductsList.some(product => productLine.to_check_product_ids.has(product))
                && (productLine.max_quantity > productLine.issued_qty || productLine.max_quantity <= 0)) {
                validBuyVoucherGetCodePrograms.push(productLine);
            };
        };
        function get_line_info(line, selected) {
            return {
                'program_name': line.reward_code_program_id[1],
                'program_id': line.reward_code_program_id[0],
                'line_id': line.id,
                'isSelected': selected || false
            }
        };
        let result = {
            validSurprisingPrograms: validSurprisingPrograms.map(line => get_line_info(line)),
            validBuyVoucherGetCodePrograms: validBuyVoucherGetCodePrograms.map(line => get_line_info(line, true))
        };
        return result;
    }

    _computeNewPriceForComboProgram(disc_total, base_total, prePrice, quantity) {
        let subTotalLine = prePrice * quantity;
        let discAmountInLine = base_total > 0.0 ? subTotalLine / base_total * disc_total : 0.0;
        let newPrice = round_decimals( (subTotalLine - discAmountInLine) / quantity, this.pos.currency.decimal_places);
        return [newPrice, prePrice - newPrice]
    }

    get_diff_amount_new_line(CodeProgram, LineList, disc_total_amount, discAmountInLine, originalPrice) {
        let diff_amount_new_line;
        diff_amount_new_line = {...LineList};
        diff_amount_new_line.promotion_usage_ids = LineList.promotion_usage_ids.map(obj => ({...obj})) || [];
        diff_amount_new_line.quantity = 1;
        LineList.quantity -= 1;

        let sub_remaining = disc_total_amount - discAmountInLine * LineList.quantity;
        diff_amount_new_line.price = originalPrice - sub_remaining;
        let new_usage = diff_amount_new_line.promotion_usage_ids.find(u => u.str_id == CodeProgram.str_id);
        new_usage.discount_amount = sub_remaining;
        new_usage.new_price = originalPrice - sub_remaining;
        return diff_amount_new_line;
    }

    applyAPricelistProgramToLineVales(PricelistItem, LineList, number_of_product) {
        let code = null;
        let activatedCodeObj = this.activatedInputCodes.find(c => c.program_id === PricelistItem.program_id)
        if (activatedCodeObj) {code = activatedCodeObj.id};
        for (let line of LineList) {
            let oldPrice = line.price;
            let fixed_price = PricelistItem.fixed_price;
            let discount_amount = (line.price - fixed_price);
            if (discount_amount > 0) {
                line.price = fixed_price;
                line.promotion_usage_ids.push(new PromotionUsageLine(
                    PricelistItem.program_id,
                    code,
                    PricelistItem.id,
                    oldPrice,
                    fixed_price,
                    discount_amount,
                    PricelistItem.str_id,
                    PricelistItem.promotion_type,
                    PricelistItem.discount_based_on
                ));
            };
        };
        return LineList;
    }

    applyACodeProgramToLineVales(CodeProgram, LineList, number_of_product, remaining_amount) {
        let code = null;
        let activatedCodeObj = this.activatedInputCodes.find(c => c.program_id === CodeProgram.id)
        if (activatedCodeObj) {code = activatedCodeObj.id};
        let diff_amount_new_line;

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

            if (LineList.is_not_discount) {
                disc_total_amount = 0;
            }

            if (remaining_amount <= disc_total_amount) {
                disc_total_amount = remaining_amount;
                remaining_amount = 0;
            } else {
                remaining_amount -= disc_total_amount;
            }

            if (disc_total_amount > 0 || LineList.is_not_discount) {
                let originalPrice = LineList.price;
                if (originalPrice*LineList.quantity <  disc_total_amount) {
                    disc_total_amount = originalPrice*LineList.quantity;
                }
                let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, LineList.quantity);
                LineList.price = newPrice;
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null,originalPrice, newPrice, discAmountInLine, CodeProgram.str_id, CodeProgram.promotion_type, CodeProgram.discount_based_on));
                if (discAmountInLine * LineList.quantity != disc_total_amount) {
                    diff_amount_new_line = this.get_diff_amount_new_line(CodeProgram, LineList, disc_total_amount, discAmountInLine, originalPrice);
                };
            } else {
                Gui.showNotification(_t(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${CodeProgram.name}.`), 3000);
            };
        } else if (CodeProgram.reward_type == "code_percent") {
            var disc_percent = CodeProgram.disc_percent;
            remaining_amount = activatedCodeObj.remaining_amount;

            if (CodeProgram.discount_apply_on == "order" && remaining_amount < disc_percent * LineList.total_price / 100 && remaining_amount > 0) {
                disc_percent = remaining_amount * 100 / LineList.total_price;
            }

            let quantity_discount = LineList.quantity;
//            if (CodeProgram.reward_quantity && CodeProgram.reward_quantity < LineList.quantity) {
//                quantity_discount = CodeProgram.reward_quantity;
//            }

            let base_total_amount = quantity_discount*LineList.price;
            let disc_total_amount = round_decimals(base_total_amount * disc_percent / 100, this.pos.currency.decimal_places);

            if (LineList.is_not_discount) {
                disc_total_amount = 0;
            }

            if (CodeProgram.discount_apply_on == "specific_products" && CodeProgram.disc_max_amount > 0) {
                if (0 < remaining_amount && remaining_amount <= disc_total_amount) {
                    disc_total_amount = remaining_amount;
                }
            }

            if (disc_total_amount > 0 || LineList.is_not_discount) {
                let originalPrice = LineList.price;
                let [newPrice, discAmountInLine] = this._computeNewPriceForComboProgram(disc_total_amount, LineList.quantity*LineList.price, originalPrice, LineList.quantity);
                LineList.price = newPrice;
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null,originalPrice, newPrice, discAmountInLine, CodeProgram.str_id, CodeProgram.promotion_type, CodeProgram.discount_based_on));
                if (discAmountInLine * LineList.quantity != disc_total_amount) {
                    diff_amount_new_line = this.get_diff_amount_new_line(CodeProgram, LineList, disc_total_amount, discAmountInLine, originalPrice);
                };
            } else {
                Gui.showNotification(_t(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${CodeProgram.name}.`), 3000);
            };
        } else if (CodeProgram.reward_type == "code_fixed_price") {
            let originalPrice = LineList.price;
            let disc_amount = originalPrice - CodeProgram.disc_fixed_price;
            disc_amount = disc_amount > 0 ? disc_amount : 0;

            if (disc_amount > 0) {
                let newPrice = CodeProgram.disc_fixed_price;
                let discAmountInLine = disc_amount;
                LineList.price = newPrice;
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null,originalPrice, newPrice, discAmountInLine, CodeProgram.str_id, CodeProgram.promotion_type, CodeProgram.discount_based_on));
            } else {
                Gui.showNotification(_t(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${CodeProgram.name}.`), 3000);
            };
        } else if (CodeProgram.reward_type == "code_buy_x_get_y") {
            LineList.reward_products = {
                'reward_product_ids': CodeProgram.reward_product_ids,
                'qty': CodeProgram.reward_quantity
            };
            if (!LineList.promotion_usage_ids) { LineList.promotion_usage_ids = [] };
            if (LineList.is_reward_line) {
                let originalPrice = LineList.price;
                let discAmountInLine = originalPrice;
                let newUsage = new PromotionUsageLine(CodeProgram.id, code, null, originalPrice, 0.0, discAmountInLine, CodeProgram.str_id, CodeProgram.promotion_type, CodeProgram.discount_based_on)
                LineList.price = 0.0;
                LineList.promotion_usage_ids.push(newUsage);
            } else {
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null, null, null, 0, CodeProgram.str_id, CodeProgram.promotion_type, CodeProgram.discount_based_on));
            }
        } else if (CodeProgram.reward_type == "code_buy_x_get_cheapest") {
            LineList.reward_products = {
                'qty': CodeProgram.reward_quantity
            };
            if (!LineList.promotion_usage_ids) { LineList.promotion_usage_ids = [] }
            if (LineList.isCheapest) {
                let originalPrice = LineList.product.lst_price ;
                let discAmountInLine = LineList.product.lst_price
                LineList.price = 0.0;
                LineList.is_reward_line = true;
                let newUsage = new PromotionUsageLine(CodeProgram.id, code, null, originalPrice, 0.0, discAmountInLine, CodeProgram.str_id, CodeProgram.promotion_type, CodeProgram.discount_based_on)
                LineList.promotion_usage_ids.push(newUsage);
                LineList.isCheapest = false;
            } else {
                LineList.promotion_usage_ids.push(new PromotionUsageLine(CodeProgram.id, code, null, null, null, 0, CodeProgram.str_id, CodeProgram.promotion_type, CodeProgram.discount_based_on));
            }
        }
        let lineListResult = [LineList];
        if (diff_amount_new_line) {
            lineListResult.push(diff_amount_new_line);
        };
        return [lineListResult, remaining_amount];
    }

    // For Combo Program
    applyAComboProgramToLineVales(program, comboLineList, number_of_combo, rewardLine) {
        let code = null;
        let activatedCodeObj = this.activatedInputCodes.find(c => c.program_id === program.id)
        if (activatedCodeObj) {code = activatedCodeObj.id};
        let diff_amount_new_line;

        comboLineList.forEach(line => {
            line['promotion_usage_ids'] = line['promotion_usage_ids'] == undefined ? [] : line['promotion_usage_ids'];
        });
        function getDiscountedAmountAPart() {
            return comboLineList.reduce((tmp_line, line) => {
                let tmp_pro = line.promotion_usage_ids.reduce((tmp, usage) => {
                    if (usage.str_id == program.str_id) {
                        tmp += usage.discount_amount * line.quantity
                    };
                    return tmp;
                }, 0);
                tmp_line += tmp_pro;
                return tmp_line;
            }, 0);
        };

        // Combo: Mua Combo, giảm tiền
        if (program.reward_type == 'combo_amount' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let disc_total_amount = program.disc_amount;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    if (comboLineList.indexOf(comboLine) == comboLineList.length-1) {
                        let discounted = getDiscountedAmountAPart();
                        let remaining_amount = disc_total_amount - discounted;
                        let newPrice = round_decimals(originalPrice - remaining_amount / comboLine.quantity, this.pos.currency.decimal_places);
                        let discAmount = originalPrice - newPrice;
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                        if (discAmount * comboLine.quantity + discounted != disc_total_amount) {
                            diff_amount_new_line = this.get_diff_amount_new_line(program, comboLine, remaining_amount, discAmount, originalPrice);
                        };
                    }
                    else {
                        let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                    };
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
                    if (comboLineList.indexOf(comboLine) == comboLineList.length-1) {
                        let discounted = getDiscountedAmountAPart();
                        let remaining_amount = disc_total_amount - discounted;
                        let newPrice = round_decimals(originalPrice - remaining_amount / comboLine.quantity, this.pos.currency.decimal_places);
                        let discAmount = originalPrice - newPrice;
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                        if (discAmount * comboLine.quantity + discounted != disc_total_amount) {
                            diff_amount_new_line = this.get_diff_amount_new_line(program, comboLine, remaining_amount, discAmount, originalPrice);
                        };
                    }
                    else {
                        let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                    };
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
                    if (comboLineList.indexOf(comboLine) == comboLineList.length-1) {
                        let discounted = getDiscountedAmountAPart();
                        let remaining_amount = disc_total_amount - discounted;
                        let newPrice = round_decimals(originalPrice - remaining_amount / comboLine.quantity, this.pos.currency.decimal_places);
                        let discAmount = originalPrice - newPrice;
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                        if (discAmount * comboLine.quantity + discounted != disc_total_amount) {
                            diff_amount_new_line = this.get_diff_amount_new_line(program, comboLine, remaining_amount, discAmount, originalPrice);
                        };
                    }
                    else {
                        let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                    };
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
                    if (comboLineList.indexOf(comboLine) == comboLineList.length-1) {
                        let discounted = getDiscountedAmountAPart();
                        let remaining_amount = disc_total_amount - discounted;
                        let newPrice = round_decimals(originalPrice - remaining_amount / comboLine.quantity, this.pos.currency.decimal_places);
                        let discAmount = originalPrice - newPrice;
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                        if (discAmount * comboLine.quantity + discounted != disc_total_amount) {
                            diff_amount_new_line = this.get_diff_amount_new_line(program, comboLine, remaining_amount, discAmount, originalPrice);
                        };
                    }
                    else {
                        let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                    };
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
        // Mua Comboo càng nhiều càng giảm, theo đơn giá cố đinh
        else if (program.reward_type == 'combo_fixed_price_by_qty' && program.promotion_type == 'combo') {
            let base_total_amount = comboLineList.reduce((accumulator, l) => {accumulator += l.quantity*l.price; return accumulator;}, 0);
            let applyRewardLine = rewardLine;
            if (!applyRewardLine) {
                return comboLineList;
            };
            let disc_total_amount = base_total_amount - applyRewardLine.disc_fixed_price;
            disc_total_amount = disc_total_amount > 0 ? disc_total_amount : 0.0;
            if (disc_total_amount > 0) {
                for (let comboLine of comboLineList) {
                    let originalPrice = comboLine.price;
                    if (comboLineList.indexOf(comboLine) == comboLineList.length-1) {
                        let discounted = getDiscountedAmountAPart();
                        let remaining_amount = disc_total_amount - discounted;
                        let newPrice = round_decimals(originalPrice - remaining_amount / comboLine.quantity, this.pos.currency.decimal_places);
                        let discAmount = originalPrice - newPrice;
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                        if (discAmount * comboLine.quantity + discounted != disc_total_amount) {
                            diff_amount_new_line = this.get_diff_amount_new_line(program, comboLine, remaining_amount, discAmount, originalPrice);
                        };
                    }
                    else {
                        let originalPrice = comboLine.price;
                        let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                        comboLine.price = newPrice;
                        comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                    };
                };
            } else {
                Gui.showNotification(_.str.sprintf(`Không tính được số tiền giảm!\n Bỏ qua việc áp dụng chương trình ${program.name}.`), 3000);
            };
        }
         // Mua Combo giảm phần trăm sản phẩm khác
        else if (program.reward_type == 'combo_discount_percent_x' && program.promotion_type == 'combo') {
            for (let comboLine of comboLineList) {
                let base_total_amount = comboLine.quantity * comboLine.price;
                let disc_total_amount = round_decimals(base_total_amount * program.disc_percent / 100, this.pos.currency.decimal_places);
                if (program.disc_max_amount > 0) {
                    disc_total_amount = disc_total_amount < program.disc_max_amount ? disc_total_amount : program.disc_max_amount;
                };
                if (program.discount_product_ids.has(comboLine.product.id)) {
                    let originalPrice = comboLine.price;
                    let [newPrice, discAmount] = this._computeNewPriceForComboProgram(disc_total_amount, base_total_amount, originalPrice, comboLine.quantity);
                    comboLine.price = newPrice;
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, originalPrice, newPrice, discAmount, program.str_id, program.promotion_type, program.discount_based_on));
                } else {
                    comboLine.promotion_usage_ids.push(new PromotionUsageLine(program.id, code, null, null, null, 0, program.str_id, program.promotion_type, program.discount_based_on));
                };
            };
        }
        if (diff_amount_new_line) {
            comboLineList.push(diff_amount_new_line);
        }
        return comboLineList;
    }

    prepareQtyOfComboByRewardLine(program, number_of_combo) {
        let rewardLines = program.rewards.sort((l1, l2) => l2.quantity_min - l1.quantity_min);
        let rewardLinesData = {}; // {reward_id: qty}
        let remaining_to_check = number_of_combo;
        for (let i = 0; i < rewardLines.length; i++) {
            if (remaining_to_check >= rewardLines[i].quantity_min) {
                while (remaining_to_check >= rewardLines[i].quantity_min) {
                    if (rewardLinesData.hasOwnProperty(rewardLines[i].id)) {
                        rewardLinesData[rewardLines[i].id] += rewardLines[i].quantity_min;
                    } else {
                        rewardLinesData[rewardLines[i].id] = rewardLines[i].quantity_min;
                    };
                    remaining_to_check -= rewardLines[i].quantity_min;
                };
            };
        };
        return rewardLinesData;
    }

    // Compute and Apply Order With list of Combo Program
    computeForListOfProgram(orderLines, listOfComboProgram, to_apply_lines) {
        to_apply_lines = to_apply_lines || {};
        let combo_count = {};
        for (const program of listOfComboProgram) {
            // Combo Program
            if (program.promotion_type == 'combo') {
                if (program.reward_type == 'combo_amount') {
                    orderLines.sort((a,b) => a.product.lst_price - b.product.lst_price)
                } else {
                    orderLines.sort((a,b) => b.product.lst_price - a.product.lst_price)
                };
                if (program.reward_type == 'combo_fixed_price_by_qty') {
                    var testNumberOfCombo = this._checkNumberOfCombo(program, orderLines, [], 0, true)[2];
                    let rewardLinesData = this.prepareQtyOfComboByRewardLine(program, testNumberOfCombo);
                    let numberOfComboPerProgram = 0;
                    if (!_.isEmpty(rewardLinesData)) {
                        for (let [reward_line_id, limit_qty_combo] of Object.entries(rewardLinesData)) {
                            let reward_line = this.pos.rewardLines.find(l => l.id == reward_line_id);
                            let [remaining, to_discount_line_vals, numberOfCombo] = this._checkNumberOfCombo(program, orderLines, [], 0, false, limit_qty_combo);
                            numberOfComboPerProgram += numberOfCombo;
                            for (let i = 0; i < to_discount_line_vals.length; i++) {
                                let result = this.applyAComboProgramToLineVales(program, to_discount_line_vals[i], numberOfCombo, reward_line);
                                if (to_apply_lines.hasOwnProperty(program.str_id)) { //  && combo_count.hasOwnProperty(program.str_id)
                                    to_apply_lines[program.str_id].push(...result);
                                } else {
                                    to_apply_lines[program.str_id] = result;
                                };
                            };
                        };
                    };
                    combo_count[program.str_id] = numberOfComboPerProgram;
                } else {
                    var [remaining, to_discount_line_vals, numberOfCombo] = this._checkNumberOfCombo(program, orderLines, [], 0);
                    if (program.reward_type == 'combo_discount_percent_x') {
                        let reward_lines = this._get_discount_product_line_for_combo(program, numberOfCombo, orderLines);
                        to_discount_line_vals.push(reward_lines);
                    }
                    combo_count[program.id] = numberOfCombo;

                    for (let i = 0; i < to_discount_line_vals.length; i++) {
                        let result = this.applyAComboProgramToLineVales(program, to_discount_line_vals[i], numberOfCombo);
                        if (to_apply_lines.hasOwnProperty(program.str_id) && combo_count.hasOwnProperty(program.str_id)) {
                            to_apply_lines[program.str_id].push(...result);
                        } else {
                            to_apply_lines[program.str_id] = result;
                        };
                    };
                };
            }
            else if (program.promotion_type == 'code') {
                let [code_to_apply_lines, remaining, code_count] = this.computeForListOfCodeProgram(orderLines, [program], to_apply_lines);
                Object.assign(combo_count, code_count);
                Object.assign(to_apply_lines, code_to_apply_lines);
            }
            // Pricelist Program
            else if (program.promotion_type == 'pricelist') {
                let [ols, to_discount_line_vals, qty] = this._checkQtyOfProductForPricelist(program, orderLines, null, to_apply_lines);
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

    computeForListOfCodeProgram(orderLines, listOfComboProgram, to_apply_lines) {
        let to_apply_lines_code = {};
        let combo_count = {};
        let orderLinesToCheck = [...orderLines];
        for (const program of listOfComboProgram) {
            // Combo Program
            if (program.promotion_type == 'code') {
                if (to_apply_lines) {
                    orderLinesToCheck.forEach((line, index) => {
                        if (line.quantity == 0) {
                            orderLinesToCheck.splice(index, 1);
                        };
                    });

//                    var to_apply_lines_other = Object.values(to_apply_lines);
                    for (const key of Object.keys(to_apply_lines)) {
                        for (let new_line of to_apply_lines[key]) {
                                let options = this._getNewLineValuesAfterDiscount(new_line);
                                if (options.quantity) {
                                    options.is_not_create = true;
                                    options.key_program = key;
                                    orderLinesToCheck.push(this._createLineFromVals(options));
                                    new_line.is_not_create = true;
                                }

                        }
                    }
                }
                if (program.reward_type == 'code_amount') {
                    orderLinesToCheck.sort((a,b) => a.product.lst_price - b.product.lst_price)
                } else {
                    orderLinesToCheck.sort((a,b) => b.product.lst_price - a.product.lst_price)
                };
                var [remaining, to_discount_line_vals, numberOfCombo, to_apply_lines_new] = this._checkNumberOfCode(program, orderLinesToCheck, [], 0, false, to_apply_lines);
                orderLinesToCheck = orderLinesToCheck.filter(l => !l.is_not_create);
                to_apply_lines = to_apply_lines_new;
                combo_count[program.id] = numberOfCombo;

                var remaining_amount = false;
//                if (program.reward_product_id_selected && numberOfCombo > 0 && program.reward_type == "code_buy_x_get_y") {
//                    let reward_products = new Set(this.pos.get_valid_reward_code_promotion(program));
//                    let available_reward_qty = to_discount_line_vals
//                                                .filter(l => reward_products.has(l.product.id))
//                                                .reduce((tmp, l) => tmp + l.quantity, 0);
//                    let product = this.pos.db.get_product_by_id(program.reward_product_id_selected);
//                    let remaining_reward_qty = numberOfCombo * program.reward_quantity - available_reward_qty;
//                    if (product && remaining_reward_qty > 0) {
//                        to_discount_line_vals.push({
//                            product: product,
//                            quantity:  remaining_reward_qty,
//                            price: product.lst_price,
//                            isNew: true,
//                            is_reward_line: true,
//                            selectedReward: true
//                        });
//                    };
//                };
                    if (numberOfCombo > 0 && program.reward_type == "code_buy_x_get_cheapest") {
                        var numberOfReward = numberOfCombo * program.reward_quantity
                        let new_to_discount_line_val;
                        for (const to_discount_line_val of to_discount_line_vals.sort((a,b) => a.price - b.price)) {
                            if (numberOfReward == to_discount_line_val.quantity) {
//                                to_discount_line_val.price = (to_discount_line_val.quantity - numberOfReward) / to_discount_line_val.quantity * to_discount_line_val.price;
                                to_discount_line_val.isCheapest = true
                                numberOfReward = 0;
                                break;
                            } else if (numberOfReward < to_discount_line_val.quantity) {
                                new_to_discount_line_val = {...to_discount_line_val};
                                new_to_discount_line_val.promotion_usage_ids = [...to_discount_line_val.promotion_usage_ids];
                                new_to_discount_line_val.quantity = numberOfReward;
                                new_to_discount_line_val.isCheapest = true;
                                to_discount_line_val.quantity = to_discount_line_val.quantity - numberOfReward;
                                numberOfReward = 0;
                                break;
                            } else {
                                numberOfReward -= to_discount_line_val.quantity;
                                to_discount_line_val.isCheapest = true;
                            }
                        };
                        if (new_to_discount_line_val) {
                            to_discount_line_vals.push(new_to_discount_line_val);
                        };
                    }
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
        };
        return [to_apply_lines, orderLines, combo_count];
    }

    autoApplyPriceListProgram(new_ol) {
        if (this.locked) return false;
        let is_with_code = (p) => p.with_code;
        if (new_ol && new_ol.quantity > 0 && !new_ol.is_applied_promotion() && new_ol.pricelist_item) {
            if (this._programIsApplicableAutomatically(new_ol.pricelist_item) && !is_with_code(new_ol.pricelist_item)) {
                this.applyAPricelistProgramToLineVales(new_ol.pricelist_item, [new_ol]);
            };
        };
        if (!new_ol) {
            let to_check_orderlines = this.get_orderlines_to_check().filter(l => l.quantity > 0 && !l.is_applied_promotion() && l.pricelist_item);
            for (let line of to_check_orderlines) {
                if (this._programIsApplicableAutomatically(line.pricelist_item) && !is_with_code(line.pricelist_item)) {
                    this.applyAPricelistProgramToLineVales(line.pricelist_item, [line]);
                };
            };
        };
    }

    async _activatePromotionCode(code) {

        if (!this.pos.promotionPrograms.some(p => p.promotion_type == 'code' || p.with_code == true)) {
            return _t('Not found an available Promotion Program needed Code to be activated');
        };

        if (this.activatedInputCodes.find((c) => c.code === code)) {
            // todo: to remove _updateActivated...
            await this._updateActivatedPromotionPrograms();
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
            const codeObj = new PosPromotionCode(
                code,
                payload.code_id,
                payload.program_id,
                payload.coupon_partner_id,
                payload.remaining_amount,
                payload.reward_for_referring,
                payload.reward_program_id,
                payload.reward_program_name
                );
            this.activatedInputCodes.push(codeObj);
            let codeProgram = this.pos.promotionPrograms.find(p => p.id == codeObj.program_id);
            codeProgram.reward_for_referring = codeObj.reward_for_referring;
            codeProgram.codes[this.access_token] = codeObj;
            if (codeProgram.promotion_type == 'pricelist') {
                this.validate_code_pricelist(codeProgram);
            };
            await this._updateActivatedPromotionPrograms();
        } else {
            return payload.error_message;
        };
        return true;
    }

    _createLineFromVals(vals) {
//        vals['lst_price'] = vals['price'];
        let obj = {is_not_create: vals['is_not_create']}
        const line = Orderline.create(obj, {pos: this.pos, order: this, ...vals});
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
            is_new_line: arg.is_new_line || false,
            pricelist_item: arg.pricelist_item,
            selectedReward: arg.selectedReward,
            merge: false,
            is_cart_discounted: arg.is_cart_discounted,
            is_not_create: arg.is_not_create
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