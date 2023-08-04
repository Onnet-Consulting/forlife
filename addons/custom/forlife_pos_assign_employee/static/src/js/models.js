odoo.define('forlife_pos_assign_employee.models', function (require) {
    "use strict";

    var {PosGlobalState, Orderline} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosCustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.assignable_employees = loadedData['assignable_employees'];
            this.assignable_employee_by_id = loadedData['assignable_employee_by_id'];
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
                return this.employee_id;
            }
        }

    Registries.Model.extend(Orderline, EmployeeOrderLine);
});
