/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';

export const PosCardRankProductScreen = (ProductScreen) => class extends ProductScreen {
    async _onClickPay() {
        const order = this.env.pos.get_order();
        const notApplied = order.get_orderlines().find(line => !line.card_rank_applied);
        if (notApplied) {
            const {confirmed} = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Card Rank Program warning'),
                body: this.env._t('Some products have not been applied to the card rank. Are you sure you want to proceed ?'),
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
