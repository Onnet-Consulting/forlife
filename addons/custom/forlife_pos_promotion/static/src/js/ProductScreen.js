/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useBarcodeReader } from 'point_of_sale.custom_hooks';

export const PosPromotionProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        async _onClickPay() {
            const order = this.env.pos.get_order();
            order.surprise_reward_program_id = null;
            const inOrderProducts = order.get_orderlines().reduce((tmp, line) => {tmp.add(line.product.id); return tmp}, new Set());
            let toCheckRewardLines = this.env.pos.surprisingRewardProducts;
            let inOrderProductsList = new Array(inOrderProducts);
            let validPrograms = [];
            for (let productLine of toCheckRewardLines) {
                if (!(inOrderProductsList.some(product => productLine.to_check_product_ids.has(product)))) {
                    validPrograms.push(this.env.pos.get_program_by_id(productLine.reward_code_program_id[0]));
                };
            };
            if (validPrograms.length > 0) {
                let programRewards = validPrograms.map(p => {
                    return {program: p, isSelected: false, id: p.id};
                });
                const { confirmed, payload } = await this.showPopup('SurpriseRewardPopup', {
                    title: this.env._t('Please select some rewards'),
                    programRewards: programRewards || [],
                });
                if (payload) {
                    order.surprise_reward_program_id = payload.id;
                }

            };
            return super._onClickPay(...arguments);
        }
    };

Registries.Component.extend(ProductScreen, PosPromotionProductScreen);
