/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class ResetPromotionProgramsButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        console.log('======================', this.env.pos);
        this.env.pos.get_order()._resetPromotionPrograms();
    }
}

ResetPromotionProgramsButton.template = 'ResetPromotionProgramsButton';

ProductScreen.addControlButton({
    component: ResetPromotionProgramsButton,
    condition: function () {
        return this.env.pos.promotionPrograms.length > 0;
    }
});

Registries.Component.add(ResetPromotionProgramsButton);
