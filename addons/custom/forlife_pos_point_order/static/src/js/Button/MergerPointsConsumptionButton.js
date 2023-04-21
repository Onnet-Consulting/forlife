odoo.define('forlife_pos_point_order.MergerPointsConsumptionButton', function (require) {
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    const rpc = require('web.rpc');
    const {onMounted, useRef, useState} = owl;

    class MergerPointsConsumptionButton extends PosComponent {
        setup() {
            super.setup();
            this.state = useState({ status: false });
            useListener('click', this.onClick);
        }

        async onClick() {
            if(!this.state.status){
                this.state.status = true;
                this.env.pos.selectedOrder.allow_for_point = true
                $('#trigger').css('background-color', 'yellow')
            }else{
                this.state.status = false;
                this.env.pos.selectedOrder.allow_for_point = false
                $('#trigger').css('background-color', '')
            }
        }

    }

    MergerPointsConsumptionButton.template = 'MergerPointsConsumptionButton';


    ProductScreen.addControlButton({
        component: MergerPointsConsumptionButton,
        condition: function () {
            return this.env.pos;
        },
    })

    Registries.Component.add(MergerPointsConsumptionButton);

    return MergerPointsConsumptionButton;
})