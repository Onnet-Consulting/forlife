odoo.define('forlife_pos_point_order.models', function (require) {
    "use strict";

    var {PosGlobalState, Orderline, Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PointsOrderLine = (Orderline) =>
        class extends Orderline {
            constructor(obj, options) {
                super(...arguments);
            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
                this.point = json.point;
            }

            clone() {
                let orderline = super.clone(...arguments);
                orderline.point = this.point;
                return orderline;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                json.point = this.point;
                return json;
            }

            set_point(point) {
                this.point = point ? parseInt(point) : null;
            }

            get_point() {
                return this.point;
            }
        };
    const PointsOrder = (Order) =>
        class extends Order {
            constructor(obj, options) {
                super(...arguments);
            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
            }

            clone() {
                let order = super.clone(...arguments);
                return order;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                return json;
            }
            get_total_with_tax() {
                var total = super.get_total_with_tax()
                var vals = 0
                for(let i =0; i<this.orderlines.length; i++){
                    if (this.orderlines[i].point){
                        vals += parseInt(this.orderlines[i].point)
                    }
                }
                return total + vals;
            }

    }
    Registries.Model.extend(Orderline, PointsOrderLine);
    Registries.Model.extend(Order, PointsOrder);
});