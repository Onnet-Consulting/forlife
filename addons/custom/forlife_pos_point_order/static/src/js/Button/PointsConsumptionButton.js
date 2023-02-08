odoo.define('forlife_pos_point_order.PointsConsumptionButton', function (require) {
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    const rpc = require('web.rpc');


    class PointsConsumptionButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        get promotion () {
            var self = this;
            let data = {
                'session_id': self.env.pos.pos_session.id,
                'date_order': self.env.pos.orders[0].creation_date,
            }
            return rpc.query({
                model: 'pos.order',
                method: 'get_program_promotion',
                args: [data],
                context: {
                     from_PointsConsumption :true
                }
            }).then(function (test) {
                    console.log(test)
            });
        }

        get order_lines(){
            return this.env.pos.get_order().get_orderlines();
        }

        async onClick() {
            var order_lines = this.order_lines;
            var promotion = await this.promotion;
            if(!this.env.pos.orders[0].partner){
                return
            }
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