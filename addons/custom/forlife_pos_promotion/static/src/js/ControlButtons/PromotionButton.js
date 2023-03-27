/** @odoo-module **/

import { Gui } from 'point_of_sale.Gui';
import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

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
        };
        console.log(order);
    }

    async onClick() {
        console.log('onClick', this.env.pos)
        const order = this.env.pos.get_order();
        // Reset Cart Program first
        order._resetCartPromotionPrograms();
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
