odoo.define('forlife_pos_product_change_refund.PosPaymentScreenChangeRefund', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const PosPaymentScreenChangeRefund = (PaymentScreen) =>
        class extends PaymentScreen {
            setup() {
                super.setup();
            }

//            async validateOrder(isForceValidate) {
//                const order = this.env.pos.get_order();
//                if (order.is_change_product || order.is_refund_product) {
//                    const orderlines = order.get_orderlines();
//                    var total = 0;
//                    for (const orderline of orderlines) {
//                        if (orderline.quantity < 0) {
//                            const old_orderline = order.get_orderline(orderline.refunded_orderline_id);
//                            if (old_orderline.point_addition > 0 || old_orderline.point_addition_event > 0) {
//                                var x = old_orderline.point_addition + old_orderline.point_addition_event;
//                            }
//                            else {
//                                total += (orderline.price * orderline.quantity);
//                            }
//                        }
//                    }
//                    console.log("AAAAAAAAAAAAAA")
//                    await super.validateOrder(...arguments);
//                }
//            }


        };

    Registries.Component.extend(PaymentScreen, PosPaymentScreenChangeRefund);

    return PosPaymentScreenChangeRefund;
});
