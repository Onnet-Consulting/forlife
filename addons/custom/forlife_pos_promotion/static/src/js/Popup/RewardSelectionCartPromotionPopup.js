odoo.define('forlife_pos_promotion.RewardSelectionCartPromotionPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');
    const { parse } = require('web.field_utils');
    const { Gui } = require('point_of_sale.Gui');
    const core = require('web.core');
    const _t = core._t;

    const { useState, onWillUnmount, onWillDestroy } = owl;

    class RewardSelectionCartPromotionPopup extends PosComponent {

        setup() {
            super.setup();
            this.state = useState({
                reward_line_vals: this.props.program.reward_line_vals || [],
                program: this.props.program,
                valid: this.props.valid,
                programOptions: this.props.programOptions,
                hasError: false,
//                additional_reward_remaining_qty: 0,
            });
            this.error_msg = '';
//            this.state.additional_reward_remaining_qty = this.state.program.max_reward_quantity - this.state.reward_line_vals.filter(l=>l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);

            onWillUnmount(() => {
                this.state.reward_line_vals.forEach(line => {
                    if (line.quantity <= 0) {
                        line.quantity = 0;
                        line.isSelected = false;
                    };
                });
                if (this.selectedQtyOnProgram() > 0) {
                    this.state.program.isSelected = true;
                } else {
                    this.state.program.isSelected = false;
                }
            });

        }

        selectedQtyOnProgram() {
            let result = this.state.reward_line_vals.filter(l => l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);
//            if (this.state.program.additional_reward_product_id) {
//                let qty = this.state.program.additional_reward_product_qty || this.state.additional_reward_remaining_qty;
//                if (qty > 0) {
//                    result += qty;
//                };
//            };
            return result;
        }

        getSelectedQtyOfLine(reward) {
            let program = this._currentProgram();
            let selected_qty_of_line = 0; // một dòng có thể đang được chọn áp dụng cho nhiều CT Hóa đơn nếu SL > 1
            this.state.programOptions.filter(p=> p.isSelected && p.id != program.id).forEach(option => {
                selected_qty_of_line += option.reward_line_vals.filter(l => l.line.cid == reward.line.cid && l.isSelected).reduce((tmp, l) => tmp + l.quantity, 0);
            });
            return selected_qty_of_line;
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
                let discAmount = reward.line.price * program.disc_percent/100;
                if (program.disc_max_amount > 0) {
                    discAmount = discAmount < program.disc_max_amount ? discAmount : program.disc_max_amount;
                };
                newPrice = reward.line.price - discAmount;
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
            let orderLines = order._get_clone_order_lines(order.get_orderlines_to_check());
            let selections = this._prepareRewardData(this.state.programOptions);
            let [to_apply_lines, remaining] = order.computeForListOfCartProgram(orderLines, selections);

            let selected_programs = this._get_selected_programs();
            let valid = true;
            let result = {};
            for (let program of selected_programs) {
                let option = this.state.programOptions.find(op=>op.id==program.id);
                let amountCheck = option.amountCheck;
                let reward_products = program.reward_type == 'cart_get_x_free' ? program.reward_product_ids : program.discount_product_ids;

                let discount_total = (to_apply_lines[program.str_id] || []).reduce((acc, line) => {
                    let amountPerLine;
                    if (program.incl_reward_in_order_type == 'no_incl') {
                        amountPerLine =
                            (!reward_products.has(line.product.id) && (program.only_condition_product ? program.valid_product_ids.has(line.product.id) : true))
                            ? line.promotion_usage_ids.filter(usage => this.env.pos.get_program_by_id(usage.str_id).promotion_type == 'cart')
                                                        .reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0)
                            : 0.0;
                    } else if (program.incl_reward_in_order_type == 'unit_price') {
                        amountPerLine =
                            (!program.only_condition_product ? reward_products.has(line.product.id) : false)
                            ? line.promotion_usage_ids.filter(usage => this.env.pos.get_program_by_id(usage.str_id).promotion_type == 'cart')
                                                        .reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0)
                            : 0.0;
                    } else {
                        amountPerLine =
                            (!program.only_condition_product || (program.only_condition_product && program.valid_product_ids.has(line.product.id)))
                            ? line.promotion_usage_ids.filter(usage => this.env.pos.get_program_by_id(usage.str_id).promotion_type == 'cart')
                                                        .reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0)
                            : 0.0;
                    };
                    return acc + amountPerLine;
                }, 0.0);
                let amount_total_after_discount = amountCheck - discount_total;
                let check = program.order_amount_min == 0
                            || (program.order_amount_min > 0 && option.required_order_amount_min <= amount_total_after_discount);

                if (check) {
                    result[program.id] = true;
                } else {
                    result[program.id] = false;
                };
            };
            if (Object.values(result).some(v => !v)) {
                valid = false;
                let invalidPro = Object.entries(result).find(([proID, val]) => !val)[0];
                Gui.showNotification(`Chương trình ${this.env.pos.get_program_by_id(invalidPro).display_name} không hợp lệ nếu áp dụng khuyến mãi dòng này!`, 3000);
            };

            let current_selected_qty = this.state.reward_line_vals.filter(l => l.isSelected).reduce((tmp, l) => tmp + l.quantity, 0)

            if (current_selected_qty > this.state.program.max_reward_quantity) {
                valid = false;
            }
            return valid;
        }

        _computeOnchangeQty(reward, input_qty) {
            let currentLine = reward;
            let quantity_input = input_qty;
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
                selected_qty_of_line += option.reward_line_vals.filter(l => l.line.cid == reward.line.cid && l.isSelected).reduce((tmp, l) => tmp + l.quantity, 0);
            })

            let qty_remaining = currentLine.line.quantity - selected_qty_of_line;
            if (qty_remaining > this.state.program.max_reward_quantity) {
                qty_remaining = this.state.program.max_reward_quantity;
            };

            // Set maximum qty of input
            currentLine.max_qty = qty_remaining;

            let quantity = quantity_input > qty_remaining ? qty_remaining : quantity_input;

            if (!this._check_valid_rewards()) {
                currentLine.quantity = 0;
                this.state.program.isSelected = false;
            } else {
                currentLine.quantity = quantity;
            }
            // Compute remaining qty of reward product
            let selectedQty_on_program = this.state.reward_line_vals.filter(l=>l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);
//            this.state.additional_reward_remaining_qty = this.state.program.max_reward_quantity - selectedQty_on_program;
//            this.state.program.additional_reward_product_qty = this.state.additional_reward_remaining_qty;
        }

        onChangeQty(reward, target) {
            let currentLine = reward;
            let quantity_input = parse.float(target.value);

            this._computeOnchangeQty(reward, quantity_input);
        }

//        onChangeAdditionalRewardProduct(target) {
//            let input = parse.integer(target.value);
//            let product = this.env.pos.db.get_product_by_id(input);
//            if (product) {
//                this.state.program.additional_reward_product_id = product.id
//            } else {
//                this.state.program.additional_reward_product_id = null;
//            }
//        }

//        onChangeAdditionalRewardQty(target) {
//            let input = parse.float(target.value);
//            if (input > this.state.additional_reward_remaining_qty) {
//                target.value = this.state.additional_reward_remaining_qty;
//            };
//            this.state.program.additional_reward_product_qty = parse.float(target.value);
//        }

        selectItem(cid) {
            let order = this.env.pos.get_order();
            let currentLine = this.state.reward_line_vals.find(l => l.line.cid === cid);
            currentLine.isSelected = !currentLine.isSelected;
            if (currentLine.isSelected) {
                this.state.program.isSelected = true;
                this._computeOnchangeQty(currentLine, 1);
            } else {
                if (this.selectedQtyOnProgram() == 0) {
                    this.state.program.isSelected = false;
                };
            };

        }

//        confirm() {
//            this.state.reward_line_vals.forEach(l => {
//                if (l.quantity <= 0) {
//                    l.isSelected = false;
//                    l.quantity = 0;
//                }
//            });
//            const valid = this._check_valid_rewards()
//            if (valid) {
//                if (this.state.reward_line_vals.some(l => l.isSelected && l.quantity > 0)) {
//                    this.state.program.isSelected = true;
//                } else {
//                    this.state.program.isSelected = false;
//                };
//                this.state.hasError = false;
//                return super.confirm();
//            } else {
//                this.state.hasError = true;
//                this.error_msg = 'Đơn hàng không đủ giá trị tối thiểu sau khi khuyến mãi!';
//                return;
//            }
//        }

//        getPayload() {
//            if (this._currentProgram().reward_type == 'cart_get_x_free' && this.state.program.additional_reward_product_id) {
//                if (!this.state.program.additional_reward_product_qty) {
//                    this.state.program.additional_reward_product_qty = this.state.additional_reward_remaining_qty;
//                }
//            }
//            super.getPayload()
//        }

//        cancel() {
//            const valid = this._check_valid_rewards()
//            if (!valid) {
//                this.state.program.isSelected = false;
//                this.state.reward_line_vals.forEach(function(l) {l.isSelected = false});
//            }
//            super.cancel()
//        }
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