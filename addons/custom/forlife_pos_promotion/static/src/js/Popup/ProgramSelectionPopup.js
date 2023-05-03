odoo.define('forlife_pos_promotion.PromotionSelectionPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState, onMounted } = owl;

    class ProgramSelectionPopup extends AbstractAwaitablePopup {

        setup() {
            super.setup();
            this.state = useState({
                programs: (this.props.programs || []).sort((p1, p2) => p2.isSelected - p1.isSelected),
                discount_total: this.props.discount_total || 0.0,
                discount_amount_order: this.props.discount_amount_order || 0,
            });
            this.combo_details = {}
            onMounted(this.selectItem);
        }

        // Thể hiện thứ tự áp dụng các CTKM, index=1 đối với CTKM nào được áp dụng đầu tiên
        _makeIndex(current_program) {
            // Increase order_apply number every selected item
            let max_order = Math.max(...this.state.programs.map(p => p.order_apply))
            if (current_program.isSelected) {
                current_program.order_apply = max_order + 1;
            };

            // Make sure index is start with Number '1'
            let clonePrograms = [...this.state.programs].filter(p => p.isSelected).sort((a, b) => a.order_apply - b.order_apply);
            let index = 1;
            let cloneProgramsDict = {};
            clonePrograms.forEach(p => {cloneProgramsDict[p.id] = index; index ++});
            this.state.programs.filter(p => p.isSelected).forEach(p => {p.index = cloneProgramsDict[p.id]});
        }

        // Set Combo Details
        setComboDetails(newLinesToApply) {
            Object.entries(newLinesToApply).forEach(
            ([k, v]) => {
            this.combo_details[k] = v;
            });
        }

        async view_combo_details(program_id) {
            if (!this.combo_details.hasOwnProperty(program_id)) {
                this.showPopup('ErrorPopup', {
                    title: 'Lỗi hiển thị',
                    body: 'Không có sản phẩm nào được áp dụng!'
                });
            };
            let program = this.env.pos.get_program_by_id(program_id);
            let qty_per_combo = program.comboFormula.reduce((total, line) => total + line.quantity, 0);
            let qty_of_combo = this.combo_details[program_id].reduce((total, line) => total + line.quantity, 0);
            let details = [];
            this.combo_details[program_id].forEach((line) => {
                let usage = line.promotion_usage_ids.find(l => l.str_id == program_id)
                if (usage && line.quantity > 0) {
                    details.push({
                        product: this.env.pos.db.get_product_by_id(line.product.id),
                        quantity: line.quantity,
                        pre_price: usage.original_price,
                        new_price: usage.new_price,
                        discount_amount: usage.discount_amount
                    });
                };
            });
            try {
                await this.showPopup('ComboDetailsPopup', {
                     title: 'Combo Details',
                     details: details,
                     program: program,
                     qty_per_combo: qty_per_combo,
                     qty_of_combo: qty_per_combo > 0 ? Math.floor(qty_of_combo/qty_per_combo) : 0,
                });
            } catch (e) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Unknown error'),
                    body: this.env._t('An unknown error prevents us from loading detail combo information.'),
                });
            };
        }

        selectItem(itemId) {
            let program_by_id = this.env.pos.get_program_by_id.bind(this.env.pos);
            this.combo_details = {};
            if (itemId !== undefined) {
                let current_program = this.state.programs.find((p) => p.id == itemId);
                current_program.isSelected = !current_program.isSelected;
                this._makeIndex(current_program);
            };

            let clone_order_lines = this.env.pos.get_order().get_orderlines_to_check().map(obj => ({...obj}));

            let selectedPrograms = this.state.programs.filter(p => p.isSelected)
                                    .sort((x, y) => x.index - y.index)
                                    .map(pro => program_by_id(pro.id));

            // Reset discounted_amount = 0.0 for programs not selected
            let not_selected_programs = this.state.programs.filter(p => !p.isSelected);
            not_selected_programs.forEach(p => p.discounted_amount = 0.0);

            let [newLinesToApply, remainingLines, combo_count] = this.env.pos.get_order().computeForListOfProgram(clone_order_lines, selectedPrograms);
//            let [newLinesToApplyCode, remainingLinesCode, code_count] = this.env.pos.get_order().computeForListOfCodeProgram(clone_order_lines, selectedPrograms, newLinesToApply);
//            newLinesToApply = newLinesToApplyCode;
//            remainingLines = remainingLinesCode

            this.setComboDetails(newLinesToApply);

            // todo: chương trình không có giảm giá thì kiểm tra promotion_usage_ids có undefined không?
            // Tính số tiền đã giảm cho mỗi chương trình đã áp dụng, và cấp số lượng combo đã áp dụng
            let discountedLines = Object.values(newLinesToApply).reduce((tmp, arr) => {tmp.push(...arr); return tmp;}, []).filter(l=>l.quantity > 0);
            for (let option of this.state.programs) {
                let amount =  discountedLines.reduce((tmp, line) => {
                    let per_line = line.promotion_usage_ids.reduce((tmp_line, u) => {
                        if (u.str_id == option.id) {
                            tmp_line += line.quantity * u.discount_amount
                        };
                        return tmp_line;
                    }, 0);
                    return tmp + per_line;
                }, 0);
                option.discounted_amount = amount;
            }
            for (let [str_id, count] of Object.entries(combo_count)) {
                this.state.programs.find(op => op.id == str_id).numberCombo = count;
            }

            // Tính tổng số tiền đã giảm trên đơn hàng
            this.state.discount_amount_order = this.state.programs.reduce((acc, p) => acc + p.discounted_amount, 0.0);

            // Tính số tiền và combo còn có thế áp dụng cho những chương trình chưa áp dụng
            const remainingLinesClone = this.env.pos.get_order()._get_clone_order_lines(remainingLines);

            let notSelectPrograms = not_selected_programs.map(p => program_by_id(p.id));
            for (let notSelectProgram of notSelectPrograms) {
                // This step to copy without reference
                let remaining_clone_order_lines = JSON.parse(JSON.stringify(remainingLinesClone));

                let newLinesToApplyClone = {};
                for (let [key, vals] of Object.entries(newLinesToApply)) {
                    newLinesToApplyClone[key] = vals.map(line => {
                        return {
                            isNew: line.isNew,
                            price: line.price,
                            product: line.product,
                            promotion_usage_ids: [...line.promotion_usage_ids],
                            quantity: line.quantity
                        }
                    });
                };

                let [newLinesToApplyNoSelected, ol, combo_count] = this.env.pos.get_order()
                        .computeForListOfProgram(remaining_clone_order_lines, [notSelectProgram], newLinesToApplyClone);

//                let [newLinesToApplyNoSelectedCode, olCode, code_count] = this.env.pos.get_order()
//                    .computeForListOfCodeProgram(remaining_clone_order_lines, [notSelectProgram], newLinesToApplyNoSelected);

//               this.setComboDetails(newLinesToApplyNoSelectedCode);
               this.setComboDetails(newLinesToApplyNoSelected);

                let discountedLinesNoSelect = Object.values(newLinesToApplyNoSelected).reduce((tmp, arr) => {tmp.push(...arr); return tmp;}, []);
                let noSelectedOption = not_selected_programs.find(op => op.id == notSelectProgram.str_id);

                noSelectedOption.forecastedNumber = combo_count[notSelectProgram.str_id];
                noSelectedOption.forecasted_discounted_amount = discountedLinesNoSelect.reduce((tmp, line) => {
                    let per_line = line.promotion_usage_ids.reduce((tmp_line, u) => {
                        if (u.str_id == noSelectedOption.id) {
                            tmp_line += line.quantity * u.discount_amount
                        };
                        return tmp_line;
                    }, 0);
                    return tmp + per_line;
                }, 0);
            };
        }

        get_valid_reward_code_promotion(program) {
            let available_products = this.env.pos.get_reward_product_ids(program);
            let valid_products_in_order = this.env.pos.get_order().get_orderlines().filter(line => program.valid_product_ids.has(line.product.id)).map(l => l.product);
            let valid_rewards = available_products.filter(p => valid_products_in_order.every(product=> product.lst_price > this.env.pos.db.get_product_by_id(p).lst_price));
            return valid_rewards
        }
        /**
         * We send as payload of the response the selected item.
         *
         * @override
         */
        getPayload() {
            self = this;
            let computePro = function(p) {
                var program = self.env.pos.get_program_by_id(p.id);
                var reward_product_id = jQuery("#reward_product_selected_"+p.id).val();
                program.reward_product_id_selected = new Set([parseInt(reward_product_id)]);
                return program;
            }
            return this.state.programs.filter(p => p.isSelected)
                                        .sort((p1, p2) => p1.index - p2.index)
                                        .map(computePro)
        }
    }
    ProgramSelectionPopup.template = 'ProgramSelectionPopup';

    ProgramSelectionPopup.defaultProps = {
        cancelText: _lt('Cancel'),
        title: _lt('Select'),
        programs: [],
        confirmKey: false,
        discount_total: 0,
    };

    Registries.Component.add(ProgramSelectionPopup);

    return ProgramSelectionPopup;
});
