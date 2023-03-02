/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';

export const PosCardRankProductScreen = (ProductScreen) => class extends ProductScreen {
    async _onClickPay() {
        const order = this.env.pos.get_order();
        const notApplied = order.get_orderlines().find(line => !line.order_line_card_rank_applied);
        if (notApplied) {
            const {confirmed} = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Customer needed'),
                body: this.env._t('eWallet requires a customer to be selected'),
            });
            if (confirmed) {
                return super._onClickPay(...arguments);
            }
        } else {
            return super._onClickPay(...arguments);
        }
    }
}

Registries.Component.extend(ProductScreen, PosCardRankProductScreen);
