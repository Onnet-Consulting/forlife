/** @odoo-module **/

import { Gui } from 'point_of_sale.Gui';
import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";
import { round_decimals,round_precision } from 'web.utils';

export class CartPromotionButton extends PosComponent {
    setup() {
        super.setup()
        useListener('click', this.onClick);
    }

    _prepareRewardData(programOptions) {
        let orderlines = this.env.pos.get_order().get_orderlines();
        let reward_data = {}
        for (let option of programOptions) {
            if (option.program.reward_type != 'cart_get_voucher' && option.isSelected && option.reward_line_vals.some(l => l.isSelected && l.quantity > 0)) {
                reward_data[option.id] = option.reward_line_vals.filter(l => l.isSelected && l.quantity > 0)
                                                .reduce((tmp, l) => {tmp[l.line.cid] = l.quantity; return tmp}, {})
            }
        };
        return reward_data;
    }

    _applyCartPromotion(optionPrograms) {
        const order = this.env.pos.get_order();
        let orderLines = order.get_orderlines();
        let selections = this._prepareRewardData(optionPrograms);
        let [newLines, remainingOrderLines] = order.computeForListOfCartProgram(orderLines, selections);
        let toRemoveLines = []
        remainingOrderLines.forEach(line => {
            let qty = line.get_quantity();
            let qty_orig = parseFloat(line.quantityStr);
            if (qty != qty_orig) {
                this.env.pos.no_restrict_reset_program = true;
                line.set_quantity(line.get_quantity());
            };
        });
        order.orderlines = order.orderlines.filter(line => line.quantity > 0)
        newLines = Object.values(newLines).reduce((list, line) => {list.push(...Object.values(line)); return list}, []);
        for (let newLine of newLines) {
            let options = order._getNewLineValuesAfterDiscount(newLine);
            order.orderlines.add(order._createLineFromVals(options));
        };

        for (let optionPro of optionPrograms) {
            if (optionPro.program.reward_type == 'cart_get_x_free' && optionPro.additional_reward_product_id && optionPro.additional_reward_product_qty > 0) {
                let product = this.env.pos.db.get_product_by_id(optionPro.additional_reward_product_id)
                let line = order._createLineFromVals({
                    product: product,
                    quantity: optionPro.additional_reward_product_qty,
                    tax_ids: product.tax_ids,
                    merge: false,
                    price: round_decimals(product.lst_price, this.env.pos.currency.decimal_places)
                });
                let to_apply_lines = order._apply_cart_program_to_orderline(optionPro.program, [line]);
                to_apply_lines.forEach( newLine => {
                    let options = order._getNewLineValuesAfterDiscount(newLine);
                    options['is_reward_line'] = true;
                    order.orderlines.add(order._createLineFromVals(options));
                });
            } else if (optionPro.program.reward_type == 'cart_get_voucher' && optionPro.voucher_program_id) {
                order.reward_voucher_program_id = optionPro.voucher_program_id[0];
                order.cart_promotion_program_id = optionPro.program.id;
            }
        };
    }

    async onClick() {
        const order = this.env.pos.get_order();
        // Reset Cart Program
        order._resetCartPromotionPrograms();
        let orderLines = order.get_orderlines();
        let programs = order.verifyCardProgramOnOrder(orderLines);
        const { confirmed, payload } = await this.showPopup('CartPromotionPopup', {
            title: this.env._t('Please select some program'),
            programs: programs,
        });
        let optionPrograms = payload;
        if (confirmed) {
            this._applyCartPromotion(optionPrograms);
        }
    }
}

CartPromotionButton.template = 'CartPromotionButton';

ProductScreen.addControlButton({
    component: CartPromotionButton,
    condition: function() {
        let order = this.env.pos.get_order()
        return order.verifyCardProgramOnOrder(order.get_orderlines()).length > 0;
    }
});

Registries.Component.add(CartPromotionButton);
