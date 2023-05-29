odoo.define('forlife_pos_promotion.CartPromotionPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState, onWillStart, onMounted } = owl;

    class CartPromotionPopup extends AbstractAwaitablePopup {

        setup() {
            super.setup();
            this.state = useState({
                programs: this.props.programs || [],
            });
            this.state.programs.forEach(option => {
                if (option.reward_line_vals) {
                    option.selectedQty = option.reward_line_vals.filter(l => l.isSelected).reduce((tmp, l) => tmp + l.quantity, 0)
                } else {
                    option.selectedQty = 0
                }
            });
        }

        async select_reward(programOption) {
            console.log('select_reward', this);
            let program = this.env.pos.get_program_by_id(String(programOption.id));
            let to_select_reward_lines;
            if (program.reward_type == 'cart_get_voucher') {
                to_select_reward_lines = [];
            } if (program.reward_type == 'cart_get_x_free') {
                to_select_reward_lines = programOption['to_reward_lines'];
            } else {
                to_select_reward_lines = programOption['to_discount_lines'];
            };

            if (programOption.reward_line_vals == undefined || programOption.reward_line_vals.length == 0) {
                programOption.reward_line_vals = to_select_reward_lines.map(line => {return {
                        line: line,
                        quantity: 0,
                        isSelected: false,
                        max_qty: line.quantity
                    }}
                ) || [];
            }
            const { confirmed, payload } = await this.showPopup('RewardSelectionCartPromotionPopup', {
                title: this.env._t('Please select some rewards'),
                reward_line_vals: programOption.reward_line_vals || [],
                program: programOption,
                programOptions: this.props.programs
            });
            this.state.programs.forEach(option => {
                if (option.reward_line_vals) {
                    option.selectedQty = option.reward_line_vals.filter(l => l.isSelected).reduce((tmp, l) => tmp + l.quantity, 0);
//                    if (option.additional_reward_product_id && option.additional_reward_product_qty > 0) {
//                        option.selectedQty += option.additional_reward_product_qty;
//                    }
                } else {
                    option.selectedQty = 0
                }
            });
        }

        getPayload() {
            return this.props.programs
        }
    };

    CartPromotionPopup.template = 'CartPromotionPopup';

    CartPromotionPopup.defaultProps = {
        cancelText: _lt('Cancel'),
        title: _lt('Select'),
        programs: [],
        confirmKey: false,
    };

    Registries.Component.add(CartPromotionPopup);

    return CartPromotionPopup;
});