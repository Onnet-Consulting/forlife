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

        get order_lines(){
            return this.env.pos.get_order().get_orderlines();
        }

        async onClick() {
            var order_lines = this.order_lines;
            const {confirmed, payload: data} = await this.showPopup('PointsConsumptionPopup', {
                startingValue: this.order_lines,
                title: this.env._t('Tiêu điểm'),
                confirmTitle: this.env._t('Xác nhận '),
                divisionpoint: this.env._t('Chia điểm'),
                cancelTitle: this.env._t('Xóa')
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