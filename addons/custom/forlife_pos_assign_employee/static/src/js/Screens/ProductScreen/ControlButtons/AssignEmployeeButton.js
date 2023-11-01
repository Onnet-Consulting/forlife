odoo.define('forlife_pos_assign_employee.AssignEmployeeButton', function (require) {
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    const {useState} = owl;


    class AssignEmployeeButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        get selectedOrderline() {
            return this.env.pos.get_order().get_selected_orderline();
        }

        listEmployees() {
            return this.env.pos.assignable_employees
        }

        get order_lines(){
            return this.env.pos.get_order().get_orderlines();
        }

        get currentEmployeeName(){
            let employeeId = this.env.pos.employeeSelected.employeeID;
            let employeeName = this.env.pos.assignable_employee_by_id[employeeId];
            return  employeeName ? employeeName : this.env._t('Nhân viên');
        }

        async onClick() {
            const selectedOrderLine = this.selectedOrderline;
            const self = this
            // if (!selectedOrderLine) return;
            const {confirmed, payload: data} = await this.showPopup('AssignEmployeePopup', {
                startingValue: self.listEmployees(),
                title: this.env._t('Assign Employee'),
                assignTitle: this.env._t('Assign employee'),
                assignAllTitle: this.env._t('Assign All'),
                assignDefaultTitle: this.env._t('Gán trước'),
                cancelTitle: this.env._t('Cancel')
            });
            if (confirmed) {
                let employee_id = data.employee_id;
                if (data.multiple) {
                    let order_lines = this.order_lines;
                    for (let line of order_lines){
                        line.set_employee(employee_id);
                    }
                } else if (data.isDefault) {
                    self.env.pos.setDefaultEmployee(employee_id);
                }
                else {
                    let order_line = await this.selectedOrderline
                    if (_.isEmpty(order_line)) {
                        this.showPopup('ErrorPopup', {
                            'title': 'Lỗi gán nhân viên',
                            'body': 'Chưa có sản phẩm không thể gán nhân viên',
                        });
                        return false;
                    }
                    order_line.set_employee(employee_id);
                }

            }
        }
    }

    AssignEmployeeButton.template = 'forlife_pos_assign_employee.AssignEmployeeButton';

    ProductScreen.addControlButton({
        component: AssignEmployeeButton,
        condition: function () {
            return this.env.pos;
        },
    })

    Registries.Component.add(AssignEmployeeButton);

    return AssignEmployeeButton;
})