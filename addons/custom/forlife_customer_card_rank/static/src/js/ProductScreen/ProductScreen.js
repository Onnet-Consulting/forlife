/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';

export const PosCardRankProductScreen = (ProductScreen) => class extends ProductScreen {
    async _onClickPay() {
        const order = this.env.pos.get_order();
        if (order.order_can_apply_card_rank() && !order.card_rank_program) {
            const {confirmed} = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Card Rank Program warning'),
                body: this.env._t('Orders have not been applied to the card rank. Are you sure you want to proceed ?'),
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
