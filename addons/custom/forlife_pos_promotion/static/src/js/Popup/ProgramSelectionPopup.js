odoo.define('forlife_pos_promotion.PromotionSelectionPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState } = owl;

    class ProgramSelectionPopup extends AbstractAwaitablePopup {

        setup() {
            super.setup();
            this.state = useState({
                programs: this.props.programs || [],
                discount_total: this.props.discount_total || 0.0,
                discount_amount_order: this.props.discount_amount_order || 0,
            });
            this.combo_details = {}
            this.selectItem(undefined);
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
            let program = this.env.pos.promotion_program_by_id[program_id];
            let qty_per_combo = program.comboFormula.reduce((total, line) => total + line.quantity, 0);
            let qty_of_combo = this.combo_details[program_id].reduce((total, line) => total + line.quantity, 0);
            let details = [];
            this.combo_details[program_id].forEach((line) => {
                let usage = line.promotion_usage_ids.find(l => l.program_id == program_id)
                if (usage) {
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

            this.setComboDetails(newLinesToApply);

            // todo: chương trình không có giảm giá thì kiểm tra promotion_usage_ids có undefined không?
            // Tính số tiền đã giảm cho mỗi chương trình đã áp dụng, và cấp số lượng combo đã áp dụng
            for (let [program_id, lines] of Object.entries(newLinesToApply)) {
                let total_amount_disc = lines.reduce((acc, line) => {
                    let amountPerLine = line.promotion_usage_ids.reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0);
                    return acc + amountPerLine
                }, 0.0);
                this.state.programs.find(p => p.id == program_id).discounted_amount = total_amount_disc;
            };
            this.state.programs.forEach(p => {
                if (combo_count.hasOwnProperty(p.id)) {
                    p.numberCombo = combo_count[p.id];
                };
            });

            // Tính tổng số tiền đã giảm trên đơn hàng
            this.state.discount_amount_order = this.state.programs.reduce((acc, p) => acc + p.discounted_amount, 0.0);

            // Tính số tiền và combo còn có thế áp dụng cho những chương trình chưa áp dụng
            const remainingLinesClone = this.env.pos.get_order()._get_clone_order_lines(remainingLines);

            let notSelectPrograms = not_selected_programs.map(p => program_by_id(p.id));
            for (let notSelectProgram of notSelectPrograms) {
                // This step to copy without reference
                let remaining_clone_order_lines = JSON.parse(JSON.stringify(remainingLinesClone));

                let [newLinesToApplyNoSelected, ol, combo_count] = this.env.pos.get_order()
                        .computeForListOfProgram(remaining_clone_order_lines, [notSelectProgram]);

               this.setComboDetails(newLinesToApplyNoSelected);

                this.state.programs.forEach(p => {
                    if (combo_count.hasOwnProperty(p.id)) {
                        p.forecastedNumber = combo_count[p.id];
                        p.forecasted_discounted_amount = 0.0;
                    };
                });
                for (let [program_id, lines] of Object.entries(newLinesToApplyNoSelected)) {
                    let forecasted_discounted_amount = lines.reduce((acc, line) => {
                        let amountPerLine = line.promotion_usage_ids.reduce((subAcc, usage) => {return subAcc + usage.discount_amount * line.quantity;}, 0.0);
                        return acc + amountPerLine
                    }, 0.0);
                    this.state.programs.find(p => p.id == program_id).forecasted_discounted_amount = forecasted_discounted_amount;
                };
            };
        }
        /**
         * We send as payload of the response the selected item.
         *
         * @override
         */
        getPayload() {
            return this.state.programs.filter(p => p.isSelected)
                                        .sort((p1, p2) => p1.index - p2.index)
                                        .map(p => this.env.pos.get_program_by_id(p.id))
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
