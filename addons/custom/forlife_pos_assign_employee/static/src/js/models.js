odoo.define('forlife_pos_assign_employee.models', function (require) {
    "use strict";

    var {PosGlobalState, Orderline, Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const {useState} = owl;


    const PosCustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {

        constructor(obj, options) {
            super(...arguments);
            this.employeeSelected = useState({
                employeeID: {}
            })
        }
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.assignable_employees = loadedData['assignable_employees'];
            this.assignable_employee_by_id = loadedData['assignable_employee_by_id'];
        }

        setDefaultEmployee(employee_id) {
            this.employeeSelected.employeeID = employee_id
        }

        getDefaultEmployee() {
            return this.employeeSelected.employeeID
        }
    }
    Registries.Model.extend(PosGlobalState, PosCustomPosGlobalState);

    const EmployeeOrderLine = (Orderline) =>
        class extends Orderline {
            constructor(obj, options) {
                super(...arguments);
                this.employee_id = this.employee_id || this.pos.user.employee_id[0];

            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
                this.employee_id = json.employee_id;
                this.assigned_employee = json.assigned_employee || '';
            }

            clone() {
                let orderline = super.clone(...arguments);
                orderline.employee_id = this.employee_id;
                return orderline;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                json.employee_id = this.employee_id;
                json.assigned_employee = this.assigned_employee;
                return json;
            }

            set_employee(employee_id) {
                this.employee_id = employee_id ? parseInt(employee_id) : null;
            }

            get_employee() {
                console.log(this.employee_id)
                return this.employee_id;
            }
        }


    const OrderAssignEmployee = (Order) => class extends Order {
        add_orderline(line) {
            if (line.pos.employeeSelected.employeeID) {
                line.set_employee(line.pos.employeeSelected.employeeID)
            }
            super.add_orderline(...arguments);
        }
    }

    Registries.Model.extend(Order, OrderAssignEmployee);

    Registries.Model.extend(Orderline, EmployeeOrderLine);
});
