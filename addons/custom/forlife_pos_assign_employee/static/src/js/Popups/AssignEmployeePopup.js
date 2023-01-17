odoo.define('forlife_pos_assign_employee.AssignEmployeePopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class AssignEmployeePopup extends PosComponent {
        setup() {
            super.setup();
        }

        get employees() {
            return this.env.pos.assignable_employees.map(function (employee) {
                return {
                    name: employee.name,
                    id: employee.id
                }
            });
        }

        cancel() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: { confirmed: false, payload: null },
            });
        }
    }

    AssignEmployeePopup.template = "AssignEmployeePopup";
    AssignEmployeePopup.defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Employee")
    };
    Registries.Component.add(AssignEmployeePopup);

    return AssignEmployeePopup;
})