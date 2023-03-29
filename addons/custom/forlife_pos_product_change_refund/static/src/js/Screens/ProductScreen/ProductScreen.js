odoo.define('forlife_pos_product_change_refund.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const RefundProductScreen = ProductScreen => class extends ProductScreen {
        async _onClickPay() {
            var currentOrder = this.currentOrder;
            var self = this;
            var missReason = false;
            if (!currentOrder.is_change_product && !currentOrder.is_refund_product) {
                return await super._onClickPay(...arguments);
            }
            _.each(currentOrder.get_orderlines(), function (orderLine) {
                if (orderLine.quantity !== 0 && orderLine.reason_refund_id === 0) {
                    missReason = true
                    self.showPopup('ErrorPopup', {
                        title: self.env._t('Missing Reason refund'),
                        body: self.env._t(
                            'Please select reason all order lines that refunding!'
                        ),
                    });
                }
            })
            if (!missReason) {
                return await super._onClickPay(...arguments);
            }
        }
    };

    Registries.Component.extend(ProductScreen, RefundProductScreen);

    return ProductScreen;

});