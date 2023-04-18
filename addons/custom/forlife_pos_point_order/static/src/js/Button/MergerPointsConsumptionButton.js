odoo.define('forlife_pos_point_order.MergerPointsConsumptionButton', function (require) {
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    const rpc = require('web.rpc');


    class MergerPointsConsumptionButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        async onClick() {
            if(!this.env.pos.allowForPoint){
                this.env.pos.allowForPoint = true;
                $('#trigger').css('background-color', 'yellow')
            }else if(this.env.pos.allowForPoint == false){
                this.env.pos.allowForPoint = true;
                $('#trigger').css('background-color', 'yellow')
            }else{
                this.env.pos.allowForPoint = false;
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