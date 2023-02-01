odoo.define('forlife_pos_point_order.PointsConsumptionButton', function (require) {
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");


    class PointsConsumptionButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        async onClick() {
            const {confirmed, payload: data} = await this.showPopup('PointsConsumptionPopup', {
                title: this.env._t('Assign Employee'),
                assignTitle: this.env._t('Assign employee'),
                assignAllTitle: this.env._t('Assign All'),
                cancelTitle: this.env._t('Cancel')
            });
        }

    }

    PointsConsumptionButton.template = 'PointsConsumptionButton';

    ProductScreen.addControlButton({
        component: PointsConsumptionButton,
        condition: function () {
            return this.env.pos;
        },
    })

    Registries.Component.add(PointsConsumptionButton);

    return PointsConsumptionButton;
})