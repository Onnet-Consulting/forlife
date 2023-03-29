/* global waitForWebfonts */
odoo.define('forlife_pos_product_change_refund.models', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    var {Order, Orderline, PosGlobalState} = require('point_of_sale.models');

    const OrderGetPhone = (Order) => class extends Order{
        get_partner_phone(){
            return this.partner ? this.partner.phone : "";
        }
        add_orderline(line){
            if(line.order.is_change_or_refund_product){
                line.is_new_line = true
            }
            super.add_orderline(...arguments);
        }

    }
    Registries.Model.extend(Order, OrderGetPhone);

    const OrderLineAddField = (Orderline) => class extends Orderline{
        constructor(obj, options) {
            super(...arguments);
            this.expire_change_refund_date = this.expire_change_refund_date || '';
            this.quantity_canbe_refund = this.quantity_canbe_refund || 0;
            this.reason_refund_id = this.reason_refund_id || 0;
        }
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.expire_change_refund_date = json.expire_change_refund_date || '';
            this.quantity_canbe_refund = json.quantity_canbe_refund || 0;
            this.reason_refund_id = json.reason_refund_id;
        }
        clone() {
            let orderline = super.clone(...arguments);
            orderline.expire_change_refund_date = this.expire_change_refund_date;
            orderline.quantity_canbe_refund = this.quantity_canbe_refund;
            orderline.reason_refund_id = this.reason_refund_id;
            return orderline;
        }
        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.expire_change_refund_date = this.expire_change_refund_date || '';
            json.quantity_canbe_refund = this.quantity_canbe_refund || 0;
            json.reason_refund_id = this.reason_refund_id;
            return json;
        }

        onchangeValue(event) {
            this.set_quantity(-parseInt(event.target.value))
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
