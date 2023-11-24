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

    const { useState, onWillUnmount, onWillDestroy, onMounted, onRendered, onWillUpdateProps } = owl;

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
            this.valid = true
            this.error_msg = '';
//            this.state.additional_reward_remaining_qty = this.state.program.max_reward_quantity - this.state.reward_line_vals.filter(l=>l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);

            onWillUnmount(() => {
                this.state.reward_line_vals.forEach(line => {
                    if (line.quantity <= 0) {
                        line.quantity = 0;
                        line.isSelected = false;
                    };
                });
                if (this.selectedQtyOnProgram(this.props.program,) > 0) {
                    this.state.program.isSelected = true;
                } else {
                    this.state.program.isSelected = false;
                }
            });

            onMounted(() => {
                const self = this
                let programValid = {};
                this.state.programOptions.filter(obj => {
                    if (!programValid[obj.program.reward_type] || obj.program.disc_percent > programValid[obj.program.reward_type].program.disc_percent) {
                        programValid[obj.program.reward_type] = obj;
                    }
                    return true;
                });

                Object.entries(programValid).some(async ([key, value]) => {
                    value.isSelected = true;
                    self.valid = self._check_valid_rewards()
                    if (!self.valid) {
                        return true;
                    }
                    if (value.reward_line_vals.length > 0) {
                        let max_qty = value.max_reward_quantity - value.reward_line_vals.filter((line) => line.isSelected).reduce((sum, r) => sum + r.line.quantity, 0)
                        if (value.program.reward_type !== 'cart_get_x_free') {
                            value.isSelected = true;
                            value.reward_line_vals.forEach(line => {
                                let qty = line.max_qty >= max_qty ? max_qty : line.max_qty;
                                line.isSelected = qty > 0;
                                line.quantity = qty < max_qty ? qty : max_qty;
                                max_qty -= qty;
                                self.valid = self._check_valid_rewards()
                            });

                        } else {
                            value.reward_line_vals.sort((r1, r2) => r2.line.product.lst_price - r1.line.product.lst_price);
                            let len_reward = value.reward_line_vals.length;
                            const totalQtyLine = value.reward_line_vals.reduce((sum, r) => sum + r.line.quantity, 0);
                            const minQtyRequired = value.required_min_quantity
                            let next_step = minQtyRequired > 0 ? minQtyRequired - 1 : 1;
                            Object.entries(value.reward_line_vals).every(async ([key, reward]) => {
                                if (reward.isSelected || max_qty <= 0) {
                                    return false;
                                }

                                if (totalQtyLine === minQtyRequired) {
                                    const qty = Math.floor(totalQtyLine / minQtyRequired)
                                    value.reward_line_vals[len_reward - 1].isSelected = qty > 0;
                                    value.reward_line_vals[len_reward - 1].quantity = qty < max_qty ? qty : max_qty;
                                    max_qty -= qty;

                                    self.valid = self._check_valid_rewards()
                                    return false;
                                } else {
                                    if (reward.line.quantity < minQtyRequired) {
                                        const qty = Math.floor(totalQtyLine / minQtyRequired)
                                        value.reward_line_vals[len_reward - 1].isSelected = qty > 0;
                                        value.reward_line_vals[len_reward - 1].quantity = qty < max_qty ? qty : max_qty;
                                        max_qty -= qty;
                                        return false;
                                    }
                                    let qty = Math.floor(reward.line.quantity / minQtyRequired)
                                    if (reward.line.quantity % minQtyRequired !== 0 && reward.line.quantity < minQtyRequired) {
                                        qty = 0
                                    }
                                    if (reward.line.quantity % minQtyRequired !== 0 && reward.line.quantity > minQtyRequired) {
                                        const qty_line = reward.line.quantity
                                        qty = qty_line >= minQtyRequired && max_qty >= value.max_reward_quantity ? Math.floor(qty_line / minQtyRequired) : max_qty
                                    }

                                    reward.isSelected = qty > 0;
                                    reward.quantity = qty < max_qty ? qty : max_qty;
                                    max_qty -= qty;

                                    self.valid = self._check_valid_rewards()
                                }
                            })
                        }
                    }
                });
            })

//            Tính năng focus vào ô input, phải tìm đúng node input vừa hành động để focus
//            onRendered(() => {
//                let rewardLine = this.state.reward_line_vals
//                                    .find(reward => this.getSelectedQtyOfLine(reward) < reward.line.quantity && reward.quantity > 0);
//                if (rewardLine && this.state.program.executingPro && this.state.program.executingPro.str_id == this.state.program.program.str_id) {
//                    let selectStr = `#quantity-${rewardLine.line.cid}p${this.state.program.program.str_id}`;
//                    let qtyInput = $(selectStr);
//                    if (qtyInput.length) {
//                        qtyInput.focus();
//                    };
//                };
//            });
        }

        hasNoDisabledNoSelectedReward() {
            let self = this;
            return this.state.reward_line_vals.some(reward => self.getSelectedQtyOfLine(reward) < reward.line.quantity && !reward.isSelected)
        }

        getDisplayStyle(reward) {
            if (!reward.isSelected && this.state.program.fixed && this.state.program.isSelected && !this.hasNoDisabledNoSelectedReward()) {
                return 'display:none'
            } else {
                return ''
            }
        }

        selectedQtyOnProgram(option) {
            let result = option.reward_line_vals.filter(l => l.isSelected && l.quantity > 0).reduce((tmp, l) => tmp + l.quantity, 0);
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
            } else if (program.reward_type == 'cart_pricelist') {
                let plItem = program.pricelistItems.find(pl => pl.product_id == reward.line.product.id);
                newPrice = plItem && plItem.fixed_price || reward.line.price;
            }
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
                let reward_products = program.reward_type == 'cart_get_x_free' ? program.reward_product_ids
                                    : program.reward_type == 'cart_pricelist' ? program.productPricelistItems
                                    : program.discount_product_ids;
                let discounted_lines = (Object.values(to_apply_lines).flat(2) || []);
                let discount_total = discounted_lines.reduce((acc, line) => {
                    let amountPerLine;
                    if (program.incl_reward_in_order_type == 'no_incl') {
                        amountPerLine =
                            (!reward_products.has(line.product.id) && (program.only_condition_product ? program.valid_product_ids.has(line.product.id) : true))
                            ? line.promotion_usage_ids.filter(usage => this.env.pos.get_program_by_id(usage.str_id).promotion_type == 'cart')
                                                        .reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0)
                            : 0.0;
                    } else if (program.incl_reward_in_order_type == 'unit_price') {
                        amountPerLine =
                            (!program.only_condition_product ? !reward_products.has(line.product.id) : false)
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

        onChangeQty(reward, value) {
            let currentLine = reward;
            let quantity_input = parse.float(value);
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

        selectItem(cid, line=null) {
            let order = this.env.pos.get_order();
            let currentLine = this.state.reward_line_vals.find(l => l.line.cid === cid) || line;
            currentLine.isSelected = !currentLine.isSelected;
            if (currentLine.isSelected) {
                this.state.program.isSelected = true;
                this._computeOnchangeQty(currentLine, 1);
//                this.state.programOptions.forEach(op => {
//                    op.executingPro = this.state.program.program;
//                });
            } else {
                if (this.selectedQtyOnProgram(this.state.program) == 0) {
                    this.state.program.isSelected = false;
                };
//                this.state.programOptions.forEach(op => {
//                    op.executingPro = null;
//                });
            };
            let otherOptions = this.state.programOptions.filter(p => p.isSelected && p.id != this.state.program.id);
            for (let option of otherOptions) {
                // Recompute floor
                let selectedQty = this.selectedQtyOnProgram(option);
                let realFloor = Math.ceil(selectedQty / option.program.reward_quantity);
                if (realFloor < option.floor) {
                    option.max_reward_quantity = realFloor * option.program.reward_quantity;
                    option.required_order_amount_min = realFloor * option.program.order_amount_min;
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