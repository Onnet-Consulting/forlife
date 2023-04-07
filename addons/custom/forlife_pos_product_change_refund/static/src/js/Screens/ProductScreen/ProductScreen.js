/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';

export const ProductScreenChangeRefund = (ProductScreen) => class extends ProductScreen {

    async _clickProduct(event) {
            if (this.currentOrder.is_refund_product) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t("Refund Order can't add new product!"),
                });
            }
            else {
                return await super._clickProduct(...arguments);
            }
        }

    async _onClickPay() {
        var lst_orderLine = [];
        var today = new Date();
        today.setHours(0, 0, 0, 0);

        const order = this.env.pos.get_order();
        const orderLines = order.get_orderlines().filter(line => !line.approvalStatus && line.expire_change_refund_date);
        if (orderLines.length > 0) {
            for (let i = 0; i < orderLines.length; i++) {
                let expire_change_refund_date = new Date(orderLines[i].expire_change_refund_date);
                expire_change_refund_date.setHours(0, 0, 0, 0);
                if (orderLines[i] && expire_change_refund_date < today) {
                    lst_orderLine.push(orderLines[i]);
                }
            }
        }
        if(lst_orderLine.length > 0){
            let products = lst_orderLine.map(song => {return song.product.display_name;});
            this.showPopup('ErrorPopup', {
                title: this.env._t('Warning'),
                body: this.env._t('Product ' + products.join(', ') + ' has expired. Please click submit to browse to continue the exchange!'),
            });
        }
        else{
//            var total_price = order.get_total_with_tax();
//            if (total_price < 0) {
//                const product_auto = this.rpc({
//                    model: product.product',
//                    method: 'get_product_auto',
//                    args: [{}],
//                })
//                if (product_auto) {
//                    order.add_product(product_auto, {price: Math.abs(total_price)});
//                }
//                return super._onClickPay(...arguments);
//            }
            return await super._onClickPay(...arguments);
        }
    }
};

Registries.Component.extend(ProductScreen, ProductScreenChangeRefund);
