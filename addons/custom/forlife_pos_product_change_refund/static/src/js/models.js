/* global waitForWebfonts */
odoo.define('forlife_pos_product_change_refund.models', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    var {Order, Orderline, PosGlobalState} = require('point_of_sale.models');

    const OrderGetPhone = (Order) => class extends Order{

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

        get_partner_phone(){
            return this.partner ? this.partner.phone : "";
        }
        add_orderline(line){
            if(line.order.is_change_product || line.order.is_refund_product){
                line.is_new_line = true
            }
            super.add_orderline(...arguments);
        }

        set_orderline_options(orderline, options) {
            if(options.expire_change_refund_date !== undefined){
                orderline.expire_change_refund_date = options.expire_change_refund_date;
            }
            if(options.quantity_canbe_refund !== undefined){
                orderline.quantity_canbe_refund = options.quantity_canbe_refund;
            }
            if (options.check_button) {
                orderline.check_button = options.check_button;
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

    }
    Registries.Model.extend(Order, OrderGetPhone);

    const OrderLineAddField = (Orderline) => class extends Orderline{
        constructor(obj, options) {
            super(...arguments);
            this.expire_change_refund_date = this.expire_change_refund_date || '';
            this.quantity_canbe_refund = this.quantity_canbe_refund || 0;
            this.reason_refund_id = this.reason_refund_id || 0;
            // manhld
            this.approvalStatus = this.approvalStatus || false;
            this.check_button = this.check_button || false;
            this.handle_change_refund_id = this.handle_change_refund_id || undefined;
            this.point_addition = this.point_addition || 0;
            this.point_addition_event = this.point_addition_event || 0;
        }
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.expire_change_refund_date = json.expire_change_refund_date || '';
            this.quantity_canbe_refund = json.quantity_canbe_refund || 0;
            this.reason_refund_id = json.reason_refund_id;
            // manhld
            this.approvalStatus = json.approvalStatus || false;
            this.check_button = json.check_button || false;
            this.handle_change_refund_id = json.handle_change_refund_id || undefined;
            this.point_addition = json.point_addition || 0;
            this.point_addition_event = json.point_addition_event || 0;
        }
        clone() {
            let orderline = super.clone(...arguments);
            orderline.expire_change_refund_date = this.expire_change_refund_date;
            orderline.quantity_canbe_refund = this.quantity_canbe_refund;
            orderline.reason_refund_id = this.reason_refund_id;
            // manhld
            orderline.approvalStatus = this.approvalStatus;
            orderline.check_button = this.check_button;
            orderline.handle_change_refund_id = this.handle_change_refund_id;
            orderline.point_addition = this.point_addition;
            orderline.point_addition_event = this.point_addition_event;
            return orderline;
        }
        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.expire_change_refund_date = this.expire_change_refund_date || '';
            json.quantity_canbe_refund = this.quantity_canbe_refund || 0;
            json.reason_refund_id = this.reason_refund_id;
            // manhld
            json.approvalStatus = this.approvalStatus || false;
            json.check_button = this.check_button || false;
            json.handle_change_refund_id = this.handle_change_refund_id || undefined;
            json.point_addition = this.point_addition || 0;
            json.point_addition_event = this.point_addition_event || 0;
            return json;
        }
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
