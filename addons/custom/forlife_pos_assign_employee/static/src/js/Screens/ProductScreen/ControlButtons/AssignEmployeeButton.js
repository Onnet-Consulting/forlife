odoo.define('forlife_pos_assign_employee.AssignEmployeeButton', function(require){
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");

    class AssignEmployeeButton extends PosComponent {
        setup(){
            super.setup();
            useListener('click', this._onClick);
        }

        _onClick() {
            console.log('clicked assign employee')
        }
    }

    AssignEmployeeButton.template = 'forlife_pos_assign_employee.AssignEmployeeButton';

    ProductScreen.addControlButton({
        component: AssignEmployeeButton,
        condition: function() {
            return true;
        },
    })

    Registries.Component.add(AssignEmployeeButton);

    return AssignEmployeeButton;
})