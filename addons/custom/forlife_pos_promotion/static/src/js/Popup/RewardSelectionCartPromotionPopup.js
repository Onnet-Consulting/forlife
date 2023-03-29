odoo.define('forlife_pos_promotion.RewardSelectionCartPromotionPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');
    const { parse } = require('web.field_utils');

    const { useState, onWillUnmount, onWillDestroy } = owl;

    class RewardSelectionCartPromotionPopup extends AbstractAwaitablePopup {

        setup() {
            super.setup();
            this.state = useState({
                reward_line_vals: this.props.reward_line_vals || [],
                program: this.props.program,
                valid: this.props.valid,
                programOptions: this.props.programOptions,
                hasError: false,
                qty_remaining: 0,
            });
            this.error_msg = '';
            this.state.qty_remaining = this.state.program.program.reward_quantity - this.state.reward_line_vals.filter(l=>l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);

            onWillUnmount(() => {
                this.state.reward_line_vals.forEach(line => {
                    if (line.quantity <= 0) {
                        line.quantity = 0;
                        line.isSelected = false;
                    };
                });
                if (this.selectedQty() > 0) {
                    this.state.program.isSelected = true;
                } else {
                    this.state.program.isSelected = false;
                }
            });

        }

        selectedQty() {
            return this.state.reward_line_vals.filter(l => l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);
        }

        pricePerUnit(reward) {
            let unit = this.env.pos.db.get_product_by_id(reward.line.product.id).get_unit().name;
            let unitPrice = this.env.pos.format_currency(reward.line.price);
            return ` ${unit} với ${unitPrice} / ${unit}`
        }

        getDiscountPrice(reward) {
            let program = this.state.program.program;
            let newPrice;
            if (program.reward_type == 'cart_discount_percent') {
                newPrice = reward.line.price * (1 - program.disc_percent/100);
            } else if (program.reward_type == 'cart_discount_fixed_price') {
                newPrice = program.disc_fixed_price;
            } else if (program.reward_type == 'cart_get_x_free') {
                newPrice = 0.0;
            };
            return `  ${this.env.pos.format_currency(newPrice)}`;
        }

        _get_selected_programs() {
            return this.state.programOptions.filter(p => p.isSelected)
            .reduce((tmp, p) => {tmp.push(p.program); return tmp}, [])
        }

        _currentProgram() {
            return this.state.program.program
        }

        _prepareRewardData(programOptions) {
            let orderlines = this.env.pos.get_order().get_orderlines();
            let reward_data = {}
            for (let option of programOptions) {
                if (option.isSelected && option.reward_line_vals.some(l => l.isSelected && l.quantity > 0)) {
                    reward_data[option.id] = option.reward_line_vals.filter(l => l.isSelected && l.quantity > 0)
                                                    .reduce((tmp, l) => {tmp[l.line.cid] = l.quantity; return tmp}, {})
                }
            };
            return reward_data;
        }

        _check_valid_rewards() {
            let program = this._currentProgram()
            let order = this.env.pos.get_order();
            let orderLines = order._get_clone_order_lines(order.get_orderlines());
            let selections = this._prepareRewardData(this.state.programOptions);
            let [to_apply_lines, remaining] = order.computeForListOfCartProgram(orderLines, selections);

            let discount_total = 0.0;
            for (let [program_id, lines] of Object.entries(to_apply_lines)) {
                discount_total += lines.reduce((acc, line) => {
                    let amountPerLine = line.promotion_usage_ids.reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0);
                    return acc + amountPerLine;
                }, 0.0);
            };
            let order_total_amount = order.get_total_with_tax();
            let amount_total_after_discount = order_total_amount - discount_total;

            let selected_programs = this._get_selected_programs();
            let valid = true;
            let result = {};
            for (let program of selected_programs) {
                if (program.incl_reward_in_order && program.order_amount_min > amount_total_after_discount) {
                    result[program.id] = false;
                } else {
                    result[program.id] = true;
                };
            };
            if (Object.values(result).some(v => !v)) {
                valid = false;
            };

            let current_selected_qty = this.state.reward_line_vals.filter(l => l.isSelected).reduce((tmp, l) => tmp + l.quantity, 0)

            if (current_selected_qty > program.reward_quantity) {
                valid = false;
            }
            return valid
        }

        onChangeQty(reward, target) {
            let currentLine = reward;
            let quantity_input = parse.float(target.value);
            currentLine.quantity = quantity_input;
            this.state.program.isSelected = true;

            if (quantity_input < 0) {
                this.state.hasError = true;
                this.error_msg = 'Số lượng sản phẩm phải là số dương!';
            } else {
                this.state.hasError = false;
                this.error_msg = '';
            }

            let program = this._currentProgram()
            let selected_qty_of_line = 0; // một dòng có thể đang được chọn áp dụng cho nhiều CT Hóa đơn nếu SL > 1
            this.state.programOptions.filter(p=> p.isSelected && p.id != program.id).forEach(option => {
                selected_qty_of_line += option.reward_line_vals.filter(l => l.line.cid == reward.line.cid).reduce((tmp, l) => tmp + l.quantity, 0);
            })

            let qty_remaining = currentLine.line.quantity - selected_qty_of_line;
            if (qty_remaining > program.reward_quantity) {
                qty_remaining = program.reward_quantity;
            };
            // Compute remaining qty of reward product
            let selectedQty_on_program = this.state.reward_line_vals.filter(l=>l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);
            this.state.qty_remaining = program.reward_quantity - selectedQty_on_program;

            // Set maximum qty of input
            currentLine.max_qty = qty_remaining;

            let quantity = quantity_input > qty_remaining ? qty_remaining : quantity_input;

            if (!this._check_valid_rewards()) {
                currentLine.quantity = 0;
                this.state.program.isSelected = false;
            } else {
                currentLine.quantity = quantity;
            }
        }

        onChangeAdditionalRewardProduct(target) {
            let input = parse.integer(target.value);
            let product = this.env.pos.db.get_product_by_id(input);
            if (product) {
                this.state.program.additional_reward_product_id = product.id
            } else {
                this.state.program.additional_reward_product_id = null;
            }
        }

        onChangeAdditionalRewardQty(target) {
            let input = parse.float(target.value);
            if (input > this.state.qty_remaining) {
                target.value = this.state.qty_remaining;
            };
            this.state.program.additional_reward_product_qty = parse.float(target.value);
        }

        selectItem(cid) {
            this.state.program.isSelected = true;
            let order = this.env.pos.get_order();
            let currentLine = this.state.reward_line_vals.find(l => l.line.cid === cid);
            currentLine.isSelected = !currentLine.isSelected;
            if (currentLine.isSelected && currentLine.quantity == 0) {
                currentLine.quantity = 1;
            };
            if (currentLine.isSelected && !this._check_valid_rewards()) {
                currentLine.quantity = 0;
            };

            // Compute remaining qty of reward product
            let selectedQty_on_program = this.state.reward_line_vals.filter(l=>l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);
            this.state.qty_remaining = this._currentProgram().reward_quantity - selectedQty_on_program;
        }

        confirm() {
            this.state.reward_line_vals.forEach(l => {
                if (l.quantity <= 0) {
                    l.isSelected = false;
                    l.quantity = 0;
                }
            });
            const valid = this._check_valid_rewards()
            if (valid) {
                if (this.state.reward_line_vals.some(l => l.isSelected && l.quantity > 0)) {
                    this.state.program.isSelected = true;
                } else {
                    this.state.program.isSelected = false;
                };
                this.state.hasError = false;
                return super.confirm();
            } else {
                this.state.hasError = true;
                this.error_msg = 'Đơn hàng không đủ giá trị tối thiểu sau khi khuyến mãi!';
                return;
            }
        }

        getPayload() {
            if (this._currentProgram().reward_type == 'cart_get_x_free' && this.state.program.additional_reward_product_id) {
                if (!this.state.program.additional_reward_product_qty) {
                    this.state.program.additional_reward_product_qty = this.state.qty_remaining;
                }
            }
            super.getPayload()
        }

        cancel() {
            const valid = this._check_valid_rewards()
            if (!valid) {
                this.state.program.isSelected = false;
                this.state.reward_line_vals.forEach(function(l) {l.isSelected = false});
            }
            super.cancel()
        }
    };

    RewardSelectionCartPromotionPopup.template = 'RewardSelectionCartPromotionPopup';

    RewardSelectionCartPromotionPopup.defaultProps = {
        cancelText: _lt('Cancel'),
        title: _lt('Select'),
        reward_line_vals: [],
        programOptions: [],
        program: null,
        valid: true,
        confirmKey: false
    };

    Registries.Component.add(RewardSelectionCartPromotionPopup);

    return RewardSelectionCartPromotionPopup;
});