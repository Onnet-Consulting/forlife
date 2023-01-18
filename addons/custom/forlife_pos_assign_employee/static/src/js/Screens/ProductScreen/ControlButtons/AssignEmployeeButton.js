odoo.define('forlife_pos_assign_employee.AssignEmployeeButton', function (require) {
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");


    class AssignEmployeeButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        get selectedOrderline() {
            return this.env.pos.get_order().get_selected_orderline();
        }

        get order_lines(){
            return this.env.pos.get_order().get_orderlines();
        }

        async onClick() {
            const selectedOrderLine = this.selectedOrderline;
            if (!selectedOrderLine) return;
            const {confirmed, payload: data} = await this.showPopup('AssignEmployeePopup', {
                startingValue: this.selectedOrderline.get_employee(),
                title: this.env._t('Assign Employee'),
                assignTitle: this.env._t('Assign employee'),
                assignAllTitle: this.env._t('Assign All'),
                cancelTitle: this.env._t('Cancel')
            });
            if (confirmed) {
                let employee_id = data.employee_id;
                if (data.multiple) {
                    let order_lines = this.order_lines;
                    for (let line of order_lines){
                        line.set_employee(employee_id);
                    }
                } else {
                    this.selectedOrderline.set_employee(employee_id);
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