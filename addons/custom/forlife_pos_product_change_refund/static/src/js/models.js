/* global waitForWebfonts */
odoo.define('forlife_pos_product_change_refund.models', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    var {Order,Orderline} = require('point_of_sale.models');

    const OrderGetPhone = (Order) => class extends Order{
        get_partner_phone(){
            return this.partner ? this.partner.phone : "";
        }
    }
    Registries.Model.extend(Order, OrderGetPhone);

    const OrderLineAddField = (Orderline) => class extends Orderline{
        constructor(obj, options) {
            super(...arguments);
            this.expire_change_refund_date = this.expire_change_refund_date || '';
            this.quantity_canbe_refund = this.quantity_canbe_refund || 0;
        }
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.expire_change_refund_date = json.expire_change_refund_date || '';
            this.quantity_canbe_refund = json.quantity_canbe_refund || 0;
        }
        clone() {
            let orderline = super.clone(...arguments);
            orderline.expire_change_refund_date = this.expire_change_refund_date;
            orderline.quantity_canbe_refund = this.quantity_canbe_refund;
            return orderline;
        }
        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.expire_change_refund_date = this.expire_change_refund_date || '';
            json.quantity_canbe_refund = this.quantity_canbe_refund || 0;
            return json;
        }
    }
    Registries.Model.extend(Orderline, OrderLineAddField);

});
