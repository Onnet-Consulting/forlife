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

        selectedQtyOnProgram(option) {
            return option.reward_line_vals.filter(l => l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);
        }

        fixProgram(option) {
            option.fixed = !option.fixed;
            if (option.isSelected) {
                if (option.fixed) {
                    // Recompute floor
                    let selectedQty = this.selectedQtyOnProgram(option);
                    let realFloor = Math.ceil(selectedQty / option.program.reward_quantity);
                    if (realFloor < option.floor) {
                        option.max_reward_quantity = realFloor * option.program.reward_quantity;
                        option.required_order_amount_min = realFloor * option.program.order_amount_min;
                    };
                } else {
                    // Reset floor
                    option.max_reward_quantity = option.floor * option.program.reward_quantity;
                    option.required_order_amount_min = option.floor * option.program.order_amount_min;
                    this.state.programs.filter(l=>l.id != option.id).forEach(option => {
                        option.reward_line_vals.forEach(line => {line.isSelected = false;});
                        option.selectedQty = 0;
                        option.isSelected = false;
                    });
                };

            } else {
                if (!option.fixed) {
                    // Reset floor
                    option.max_reward_quantity = option.floor * option.program.reward_quantity;
                    option.required_order_amount_min = option.floor * option.program.order_amount_min;
                    this.state.programs.filter(l=>l.id != option.id).forEach(option => {
                        option.reward_line_vals.forEach(line => {line.isSelected = false;});
                        option.selectedQty = 0;
                        option.isSelected = false;
                    });
                } else {
                    if (option.floor > 1) {
                        option.max_reward_quantity = (option.floor - 1) * option.program.reward_quantity;
                        option.required_order_amount_min = (option.floor - 1) * option.program.order_amount_min;
                    };
                };
            };
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