odoo.define('forlife_pos_point_order.OrderlineDetails', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    const OrderlineDetails = require('point_of_sale.OrderlineDetails');

    const OrderlineDetailsPoints = OrderlineDetails => class extends OrderlineDetails {
        getPointOrderLine() {
            return this.props.line.point || '';
        }
    }

    Registries.Component.extend(OrderlineDetails, OrderlineDetailsPoints);

    return OrderlineDetailsPoints;

});