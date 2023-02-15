odoo.define('forlife_pos_point_order.models', function (require) {
    "use strict";

    var {PosGlobalState, Orderline} = require('point_of_sale.models');
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
//    const PointsOrder = (Order) =>
//        class extends Order {
//            constructor(obj, options) {
//                super(...arguments);
//            }
//
//            init_from_JSON(json) {
//                super.init_from_JSON(...arguments);
//                this.point_format = json.point_format;
//                this.point_forlive = json.point_forlive;
//            }
//
//            clone() {
//                let order = super.clone(...arguments);
//                order.point_format = this.point_format;
//                order.point_forlive = this.point_forlive;
//                return order;
//            }
//
//            export_as_JSON() {
//                const json = super.export_as_JSON(...arguments);
//                json.point_format = this.point_format;
//                json.point_forlive = this.point_forlive;
//                return json;
//            }
//        }

    Registries.Model.extend(Orderline, PointsOrderLine);
});