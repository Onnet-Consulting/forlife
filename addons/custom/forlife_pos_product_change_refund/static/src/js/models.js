/* global waitForWebfonts */
odoo.define('forlife_pos_product_change_refund.models', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    var {Order, Orderline, PosGlobalState} = require('point_of_sale.models');
    var core = require('web.core');
    const _t = core._t;
    var { Gui } = require('point_of_sale.Gui');
    const OrderGetPhone = (Order) => class extends Order {

        constructor(obj, options) {
            super(...arguments);
            this.approved = this.approved || false;
            this.is_refund_product = this.is_refund_product || false;
            this.is_change_product = this.is_change_product || false;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.approved = json.approved || false;
            this.is_refund_product = json.is_refund_product || false;
            this.is_change_product = json.is_change_product || false;
        }

        clone() {
            let order = super.clone(...arguments);
            order.approved = this.approved;
            order.is_refund_product = this.is_refund_product;
            order.is_change_product = this.is_change_product;
            return order;
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.approved = this.approved || false;
            json.is_refund_product = this.is_refund_product || false;
            json.is_change_product = this.is_change_product || false;
            return json;
        }

        get_partner_phone() {
            return this.partner ? this.partner.phone : "";
        }

        add_orderline(line) {
            if (line.order.is_change_product) {
                line.is_new_line = true
            }
            super.add_orderline(...arguments);
        }

        set_orderline_options(orderline, options) {
            if (options.expire_change_refund_date !== undefined) {
                orderline.expire_change_refund_date = options.expire_change_refund_date;
            }
            if (options.quantity_canbe_refund !== undefined) {
                orderline.quantity_canbe_refund = options.quantity_canbe_refund;
            }
            if (options.money_is_reduced !== 0) {
                orderline.money_is_reduced = options.money_is_reduced;
            }
            if (options.price !== undefined && options.quantity) {
                orderline.money_is_reduced = (orderline.price - options.price) * options.quantity;
            }
            if (options.money_point_is_reduced !== 0) {
                orderline.money_point_is_reduced = options.money_point_is_reduced;
            }
            if (options.check_button) {
                orderline.check_button = options.check_button;
            }
            if (options.is_product_defective !== undefined) {
                orderline.is_product_defective = orderline.is_product_defective
            }
            if (options.money_reduce_from_product_defective !== 0) {
                orderline.money_reduce_from_product_defective = options.money_reduce_from_product_defective;
            }
            if (options.product_defective_id !== 0) {
                orderline.product_defective_id = options.product_defective_id;
            }
            if (options.pos_order_line_discount_details){
                orderline.pos_order_line_discount_details = options.pos_order_line_discount_details;
            }
            super.set_orderline_options(...arguments);
        }

        remove_orderline(line) {
            if (line.handle_change_refund_id) {
                var args = {};
                args.id = line.handle_change_refund_id;
                this.pos.env.services.rpc({
                    model: 'handle.change.refund',
                    method: 'cancel_rc_handle_change_refund',
                    args: [args],
                })
            }
            super.remove_orderline(...arguments);
        }

        get_total_with_tax() {
            var total = super.get_total_with_tax()
            var defective = 0
            var reduced = 0;
            for (let i = 0; i < this.orderlines.length; i++) {
                if (this.orderlines[i].is_product_defective) {
                    defective += parseInt(this.orderlines[i].money_reduce_from_product_defective)
                }
                if (this.orderlines[i].quantity_canbe_refund > 0 && !this.orderlines[i].beStatus) {
                    reduced += (this.orderlines[i].money_is_reduced * Math.abs(this.orderlines[i].get_quantity())) / this.orderlines[i].quantity_canbe_refund;
                }
            }
            return total - defective + reduced;
        }

    }
    Registries.Model.extend(Order, OrderGetPhone);

    const OrderLineAddField = (Orderline) => class extends Orderline {
        constructor(obj, options) {
            super(...arguments);
            this.expire_change_refund_date = this.expire_change_refund_date || '';
            this.quantity_canbe_refund = this.quantity_canbe_refund || 0;
            this.reason_refund_id = this.reason_refund_id || 0;
            // manhld
            this.approvalStatus = this.approvalStatus || false;
            this.beStatus = this.beStatus || false;
            this.check_button = this.check_button || false;
            this.is_new_line = this.is_new_line || false;
            this.is_promotion = this.is_promotion || false;
            this.handle_change_refund_id = this.handle_change_refund_id || undefined;
            this.money_is_reduced = this.money_is_reduced || 0;
            this.money_point_is_reduced = this.money_point_is_reduced || 0;
//            this.price_unit_refund = this.price_unit_refund ||0;
//            this.price_subtotal_incl_refund = this.price_subtotal_incl_refund ||0;
            this.is_product_defective = this.is_product_defective || false;
            this.money_reduce_from_product_defective = this.money_reduce_from_product_defective || 0;
            this.product_defective_id = this.product_defective_id || 0;
            this.subtotal_paid = this.subtotal_paid || 0;
            this.pos_order_line_discount_details = this.pos_order_line_discount_details || [];
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.expire_change_refund_date = json.expire_change_refund_date || '';
            this.quantity_canbe_refund = json.quantity_canbe_refund || 0;
            this.reason_refund_id = json.reason_refund_id;
            // manhld
            this.approvalStatus = json.approvalStatus || false;
            this.beStatus = json.beStatus || false;
            this.check_button = json.check_button || false;
            this.is_new_line = json.is_new_line || false;
            this.is_promotion = json.is_promotion || false;
            this.handle_change_refund_id = json.handle_change_refund_id || undefined;
            this.money_is_reduced = json.money_is_reduced || 0;
            this.money_point_is_reduced = json.money_point_is_reduced || 0;
//            this.price_unit_refund = json.price_unit_refund || 0;
//            this.price_subtotal_incl_refund = json.price_subtotal_incl_refund || 0;
            this.is_product_defective = json.is_product_defective || false;
            this.money_reduce_from_product_defective = json.money_reduce_from_product_defective || 0;
            this.product_defective_id = json.product_defective_id || 0;
            this.subtotal_paid = json.subtotal_paid || 0;
            this.pos_order_line_discount_details = json.pos_order_line_discount_details || [];
        }

        clone() {
            let orderline = super.clone(...arguments);
            orderline.expire_change_refund_date = this.expire_change_refund_date;
            orderline.quantity_canbe_refund = this.quantity_canbe_refund;
            orderline.reason_refund_id = this.reason_refund_id;
            // manhld
            orderline.approvalStatus = this.approvalStatus;
            orderline.beStatus = this.beStatus;
            orderline.check_button = this.check_button;
            orderline.is_new_line = this.is_new_line;
            orderline.is_promotion = this.is_promotion;
            orderline.handle_change_refund_id = this.handle_change_refund_id;
            orderline.money_is_reduced = this.money_is_reduced;
            orderline.money_point_is_reduced = this.money_point_is_reduced;
//            orderline.price_unit_refund = this.price_unit_refund;
//            orderline.price_subtotal_incl_refund = this.price_subtotal_incl_refund;
            orderline.is_product_defective = this.is_product_defective;
            orderline.money_reduce_from_product_defective = this.money_reduce_from_product_defective;
            orderline.product_defective_id = this.product_defective_id;
            orderline.subtotal_paid = this.subtotal_paid || 0;
            orderline.pos_order_line_discount_details = this.pos_order_line_discount_details || [];
            return orderline;
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.expire_change_refund_date = this.expire_change_refund_date || '';
            json.quantity_canbe_refund = this.quantity_canbe_refund || 0;
            json.reason_refund_id = this.reason_refund_id;
            // manhld
            json.approvalStatus = this.approvalStatus || false;
            json.beStatus = this.beStatus || false;
            json.check_button = this.check_button || false;
            json.is_new_line = this.is_new_line || false;
            json.is_promotion = this.is_promotion || false;
            json.handle_change_refund_id = this.handle_change_refund_id || undefined;
            json.money_is_reduced = this.money_is_reduced || 0;
            json.money_point_is_reduced = this.money_point_is_reduced || 0;
//            json.price_unit_refund = this.price_unit_refund || 0;
//            json.price_subtotal_incl_refund = this.price_subtotal_incl_refund || 0;
            json.is_product_defective = this.is_product_defective || false;
            json.money_reduce_from_product_defective = this.money_reduce_from_product_defective || 0;
            json.product_defective_id = this.product_defective_id || 0;
            json.subtotal_paid = this.subtotal_paid || 0;
            json.pos_order_line_discount_details = this.pos_order_line_discount_details || [];
            return json;
        }

        set_quantity(quantity, keep_price){
            if(this.is_product_defective && quantity > 1){
                    Gui.showPopup('ErrorPopup', {
                        title: _t('Warning'),
                        body: _t('Hành động sửa số lượng trên sản phẩm này bị cấm !')
                    });
                    return;
            }
            return super.set_quantity(quantity, keep_price)
        }

        get_price_with_tax() {
            var reduced = 0;
            var total = super.get_price_with_tax();
            if (this.money_reduce_from_product_defective > 0) {
                total -= this.money_reduce_from_product_defective
            }

            if (this.quantity_canbe_refund > 0 && !this.beStatus) {
                reduced += (this.money_is_reduced * Math.abs(this.get_quantity())) / this.quantity_canbe_refund;
            }
            return total + reduced;
        }

        getTotalDiscountLineDefective() {
            var total = 0;
            if (this.money_reduce_from_product_defective > 0) {
                total += this.money_reduce_from_product_defective
            }
            return total;
        }

//        get_price_without_tax() {
//            var total = super.get_price_without_tax();
//            var vals = 0;
//            if (this.order.is_change_product && !this.is_new_line) {
//                vals += (this.money_point_is_reduced /this.quantity_canbe_refund) * this.quantity;
//            }
//            return total + vals;
//        }
    }
    Registries.Model.extend(Orderline, OrderLineAddField);

    const ReasonRefundPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.pos_reason_refund = loadedData['pos.reason.refund'];
        }
    }
    Registries.Model.extend(PosGlobalState, ReasonRefundPosGlobalState);

});
