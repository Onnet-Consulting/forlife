odoo.define('forlife_pos_product_change_refund.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const RefundProductScreen = ProductScreen => class extends ProductScreen {

        async _clickProduct(event) {
            if (this.currentOrder.is_refund_product) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t("Refund Order can't add new product!"),
                });
            } else {
                return await super._clickProduct(...arguments);
            }
        }

        async _onClickPay() {
            // manhld
            var self = this;
            var lst_orderLine = [];
            var today = new Date();
            today.setHours(0, 0, 0, 0);

            const order = this.env.pos.get_order();
            const orderLines = order.get_orderlines().filter(line => !line.beStatus && line.expire_change_refund_date);
            if (orderLines.length > 0) {
                for (let i = 0; i < orderLines.length; i++) {
                    let expire_change_refund_date = new Date(orderLines[i].expire_change_refund_date);
                    expire_change_refund_date.setHours(0, 0, 0, 0);
                    if (orderLines[i] && expire_change_refund_date < today && Math.abs(orderLines[i].quantity) > 0) {
                        lst_orderLine.push(orderLines[i]);
                    }
                }
            }
            if (lst_orderLine.length > 0) {
                let products = lst_orderLine.map(song => {
                    return song.product.display_name;
                });
                self.showPopup('ErrorPopup', {
                    title: self.env._t('Warning'),
                    body: self.env._t('Product ' + products.join(', ') + ' has expired. Please click submit to browse to continue the exchange!'),
                });
                return;
            }
            else {
                // tuuh
                var currentOrder = this.currentOrder;
                var missReason = false;
                if (!currentOrder.is_change_product && !currentOrder.is_refund_product) {
                    return await super._onClickPay(...arguments);
                }
                _.each(currentOrder.get_orderlines(), function (orderLine) {
                    if (orderLine.quantity !== 0 && orderLine.reason_refund_id === 0 && !orderLine.is_new_line) {
                        missReason = true
                        self.showPopup('ErrorPopup', {
                            title: self.env._t('Missing Reason refund'),
                            body: self.env._t(
                                'Please select reason all order lines that refunding!'
                            ),
                        });
                        return;
                    }
                })
                if (!missReason) {
                    if (currentOrder.is_change_product) {
                        var total_price = order.get_total_with_tax();
                        if (total_price < 0) {
                            const product_auto_id = await this.rpc({
                                model: 'product.product',
                                method: 'get_product_auto',
                            })
                            if (product_auto_id) {
                                const product_auto = this.env.pos.db.get_product_by_id(product_auto_id);
                                order.add_product(product_auto, {price: Math.abs(total_price)});
                            }
                        }
                    }
                    return await super._onClickPay(...arguments);
                }
            }

        }

    };

    Registries.Component.extend(ProductScreen, RefundProductScreen);

    return ProductScreen;

});