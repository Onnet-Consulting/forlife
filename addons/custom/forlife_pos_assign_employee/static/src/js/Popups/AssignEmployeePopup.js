odoo.define('forlife_pos_assign_employee.AssignEmployeePopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');


    class AssignEmployeePopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({
                employeeID: this.get_default_employee()
            })
        }

        get_default_employee() {
            let employees = this.env.pos.assignable_employees;
            return employees && employees[0].id;
        }

        get employees() {
            return this.env.pos.assignable_employees.map(function (employee) {
                return {
                    name: employee.name,
                    id: employee.id
                }
            });
        }

        get selectedLine() {
            return this.env.pos.get_order().get_selected_orderline();
        }

        cancel() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: false, payload: null},
            });
        }


        confirm() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: true, payload: this.getSingleLinePayload()},
            });
        }

        confirm_all() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: true, payload: this.getMultipleLinesPayload()},
            });
        }

        getMultipleLinesPayload() {
            return {
                employee_id: this.state.employeeID,
                multiple: true
            }
        }

        getSingleLinePayload() {
            return {
                employee_id: this.state.employeeID,
                multiple: false
            }
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