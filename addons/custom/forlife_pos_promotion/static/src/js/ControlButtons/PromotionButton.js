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
        let [newLines, remainingOrderLines, combo_count] = order.computeForListOfCombo(order_lines, selectedProgramsList);
        remainingOrderLines.forEach(line => {
            line.set_quantity(line.get_quantity());
            if (line.quantity === 0) {
                order.orderlines.remove(line)
            };
        });

        newLines = Object.values(newLines).reduce((list, line) => {list.push(...Object.values(line)); return list}, []);
        for (let newLine of newLines) {
            let options = order._getNewLineValuesAfterDiscount(newLine);
            order.orderlines.add(order._createLineFromVals(options));
        };
    }

    async onClick() {
        console.log('onClick', this.env.pos)
        const order = this.env.pos.get_order();
        const potentialPrograms = order.getPotentialProgramsToSelect();
        if (potentialPrograms.size === 0) {
            await this.showPopup('ErrorPopup', {
                title: this.env._t('No program available.'),
                body: this.env._t('There are no program applicable for this customer. Add more product and try again.')
            });
            return false;
        };
        const programsList = potentialPrograms.map((pro) => ({
            id: pro.program.id,
            label: pro.program.name,
            isSelected: false,
            forecastedNumber: pro.number,
            order_apply: -1,
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
        return this.env.pos.get_order().getActivatedComboPrograms().length > 0;
    }
});

Registries.Component.add(PromotionButton);
