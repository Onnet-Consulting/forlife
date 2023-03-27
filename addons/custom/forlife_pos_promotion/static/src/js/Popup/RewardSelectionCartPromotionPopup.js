odoo.define('forlife_pos_promotion.RewardSelectionCartPromotionPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');
    const { parse } = require('web.field_utils');

    const { useState } = owl;

    class RewardSelectionCartPromotionPopup extends AbstractAwaitablePopup {

        setup() {
            super.setup();
            this.state = useState({
                reward_line_vals: this.props.reward_line_vals || [],
                program: this.props.program,
                valid: this.props.valid,
                programOptions: this.props.programOptions,
                hasError: false
            });
            this.error_msg = '';
        }

        pricePerUnit(reward) {
            let unit = this.env.pos.db.get_product_by_id(reward.line.product.id).get_unit().name;
            let unitPrice = this.env.pos.format_currency(reward.line.price);
            return ` ${unit} với ${unitPrice} / ${unit}`
        }

        _get_selected_programs() {
            return this.state.programOptions.filter(p => p.isSelected).reduce((tmp, p) => {tmp.push(p.program); return tmp}, [])
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
            for (let program of selected_programs) {
                if (program.order_amount_min > amount_total_after_discount) {
                    valid = false;
                    break;
                };
            };
            return valid
        }

        onChangeQty(cid, target) {
            let order = this.env.pos.get_order();
            let orderLines = order._get_clone_order_lines(order.get_orderlines())
            let currentLine = this.state.reward_line_vals.find(l=> l.line.cid === cid);
            let selected_qty = 0;
            this.state.programOptions.filter(p=>p.isSelected).forEach(option => {
                selected_qty += option.reward_line_vals.filter(l => l.line.cid == cid).reduce((tmp, l) => tmp + l.quantity, 0)
            })
            let qty_remaining = currentLine.line.quantity - selected_qty
            currentLine.max_qty = qty_remaining;
            let quantity_input = parse.float(target.value);
            let quantity = quantity_input > qty_remaining ? qty_remaining : quantity_input;

            this.state.program.isSelected = true;
            currentLine.quantity = quantity;
            if (!this._check_valid_rewards()) {
                currentLine.quantity = 0;
                this.state.program.isSelected = false;
            }
        }

        selectItem(cid) {
            let order = this.env.pos.get_order();
            let currentLine = this.state.reward_line_vals.find(l => l.line.cid === cid);
            currentLine.isSelected = !currentLine.isSelected;
        }

        confirm() {
            const valid = this._check_valid_rewards()
            if (valid) {
                if (this.state.reward_line_vals.some(l => l.isSelected && l.quantity > 0)) {
                    this.state.program.isSelected = true;
                } else {
                    this.state.program.isSelected = false;
                };
                return super.confirm();
            } else {
                this.state.hasError = true;
                this.error_msg = 'Đơn hàng không đủ giá trị tối thiểu sau khi khuyến mãi!';
                return;
            }
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