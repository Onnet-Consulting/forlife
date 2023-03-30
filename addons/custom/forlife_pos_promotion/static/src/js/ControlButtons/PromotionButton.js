/** @odoo-module **/

import { Gui } from 'point_of_sale.Gui';
import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";
import { round_decimals,round_precision } from 'web.utils';

export class PromotionButton extends PosComponent {
    setup() {
        super.setup()
        useListener('click', this.onClick);
    }

    async _applyPromotionProgram(selectedProgramsList) {
        const order = this.env.pos.get_order();
        let order_lines = order.get_orderlines_to_check();
        let [newLines, remainingOrderLines, combo_count] = order.computeForListOfProgram(order_lines, selectedProgramsList);
        remainingOrderLines.forEach(line => {
            let qty = line.get_quantity();
            let qty_orig = parseFloat(line.quantityStr);
            if (qty != qty_orig) {
                line.set_quantity(line.get_quantity());
            };
            if (line.quantity == 0) {
                order.remove_orderline(line);
            };
        });

        newLines = Object.values(newLines).reduce((list, line) => {list.push(...Object.values(line)); return list}, []);
        for (let newLine of newLines) {
            let options = order._getNewLineValuesAfterDiscount(newLine);
            order.orderlines.add(order._createLineFromVals(options));
        }
        for (let newLine of newLines) {
            if (newLine.hasOwnProperty('reward_products')) {
                if (newLine.reward_products.reward_product_ids) {
                    var quantity_reward = newLine.reward_products.qty;
                    order.orderlines.forEach(line => {
                        if (line.product.id in newLine.reward_products.reward_product_ids) {
                            if (line.quantity >= quantity_reward && line.price > 0 && quantity_reward) {
                                line.price = round_decimals(line.price * (line.quantity - quantity_reward ) / line.quantity, this.env.pos.currency.decimal_places);
                                quantity_reward = 0;
                            } else if (line.quantity < newLine.reward_products.qty && line.price > 0 && quantity_reward) {
                                line.price = round_decimals(0, this.env.pos.currency.decimal_places);
                                quantity_reward -= line.quantity;
                            }
                        }
                    });

                    if (quantity_reward) {
                        let product = this.env.pos.db.get_product_by_id([...newLine.reward_products.reward_product_ids][0]);
                        order.orderlines.add(order._createLineFromVals({
                            product: product,
                            price: round_decimals(0, this.env.pos.currency.decimal_places),
                            tax_ids: product.tax_ids,
                            quantity: quantity_reward,
                            is_reward_line: true,
                            merge: false,
                        }));
                    }
                } else {
                    var quantity_reward = newLine.reward_products.qty;
                    order.orderlines.sort((a,b) => a.product.lst_price - b.product.lst_price).forEach(line => {
                        if (line.quantity >= quantity_reward && line.price > 0 && quantity_reward) {
                            line.price = round_decimals(line.price * (line.quantity - quantity_reward ) / line.quantity, this.env.pos.currency.decimal_places);
                            quantity_reward = 0;
                        } else if (line.quantity < newLine.reward_products.qty && line.price > 0 && quantity_reward) {
                            line.price = round_decimals(0, this.env.pos.currency.decimal_places);
                            quantity_reward -= line.quantity;
                        }
                    })
                }
            }
        };
    }

    async onClick() {
        console.log('onClick', this.env.pos)
        const order = this.env.pos.get_order();
        const potentialPrograms = order.getPotentialProgramsToSelect();
        let bestCombine = order.computeBestCombineOfProgram() || [];
        bestCombine = bestCombine.map(p => this.env.pos.get_program_by_id(p))
        if (potentialPrograms.size === 0) {
            await this.showPopup('ErrorPopup', {
                title: this.env._t('No program available.'),
                body: this.env._t('There are no program applicable for this customer. Add more product and try again.')
            });
            return false;
        };
        const programsList = potentialPrograms.map((pro) => ({
            id: pro.program.str_id,
            label: pro.program.display_name,
            isSelected: bestCombine.length > 0 ? bestCombine.includes(pro.program) : false,
            index: bestCombine.length > 0 ? bestCombine.indexOf(pro.program) + 1 : -1,
            forecastedNumber: pro.number,
            order_apply: bestCombine.length > 0 ? bestCombine.indexOf(pro.program) + 1 : -1,
            discounted_amount: 0.0,
            forecasted_discounted_amount: 0.0,
            reward_type: pro.program.reward_type,
            reward_product_ids: pro.program.reward_product_ids
        }));

        const { confirmed, payload } = await this.showPopup('ProgramSelectionPopup', {
            title: this.env._t('Please select some program'),
            programs: programsList,
            discount_total: 0,
        });
        if (confirmed) {
            return this._applyPromotionProgram(payload);
        };
        return false;
    }
}

PromotionButton.template = 'PromotionButton';

ProductScreen.addControlButton({
    component: PromotionButton,
    condition: function() {
        return this.env.pos.get_order().getActivatedPrograms().length > 0;
    }
});

Registries.Component.add(PromotionButton);
