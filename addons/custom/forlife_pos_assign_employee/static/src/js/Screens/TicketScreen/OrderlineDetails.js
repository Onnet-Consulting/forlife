odoo.define('forlife_pos_assign_employee.OrderlineDetails', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    const OrderlineDetails = require('point_of_sale.OrderlineDetails');

    const OrderlineDetailsEmployee = OrderlineDetails => class extends OrderlineDetails {
        getAssignedEmployeeName() {
            return this.props.line.assigned_employee || '';
        }
    }

    Registries.Component.extend(OrderlineDetails, OrderlineDetailsEmployee);

    return OrderlineDetailsEmployee;

});