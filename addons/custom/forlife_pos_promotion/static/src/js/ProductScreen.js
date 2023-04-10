/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useBarcodeReader } from 'point_of_sale.custom_hooks';

export const PosPromotionProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        async _onClickPay() {
            const order = this.env.pos.get_order();
            order.surprise_reward_program_id = null;
            order.surprising_reward_line_id = null;
            const inOrderProducts = order.get_orderlines().reduce((tmp, line) => {tmp.add(line.product.id); return tmp}, new Set());
            let toCheckRewardLines = this.env.pos.surprisingRewardProducts;
            let inOrderProductsList = new Array(...inOrderProducts);
            let validPrograms = [];
            for (let productLine of toCheckRewardLines) {
                if (!inOrderProductsList.some(product => productLine.to_check_product_ids.has(product)) && productLine.max_quantity > productLine.issued_qty) {
                    validPrograms.push(
                        [productLine.id, productLine.reward_code_program_id[0], productLine.reward_code_program_id[1]]
                    );
                };
            };
            if (validPrograms.length > 0 && order.get_partner()) {
                let programRewards = validPrograms.map((line) => {
                    return {program_name: line[2], program_id: line[1], line_id: line[0], isSelected: false};
                });
                const { confirmed, payload } = await this.showPopup('SurpriseRewardPopup', {
                    title: this.env._t('Please select some rewards'),
                    programRewards: programRewards || [],
                });
                if (payload) {
                    order.surprise_reward_program_id = payload.program_id;
                    order.surprising_reward_line_id = payload.line_id;
                }

            };
            return super._onClickPay(...arguments);
        }
    };

Registries.Component.extend(ProductScreen, PosPromotionProductScreen);
