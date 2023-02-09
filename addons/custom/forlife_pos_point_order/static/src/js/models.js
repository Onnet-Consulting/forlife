odoo.define('forlife_pos_assign_employee.models', function (require) {
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
        }

    Registries.Model.extend(Orderline, PointsOrderLine);