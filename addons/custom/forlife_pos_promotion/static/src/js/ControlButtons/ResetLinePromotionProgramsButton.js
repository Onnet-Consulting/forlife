/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class ResetLinePromotionProgramsButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        let selected_line = this.env.pos.get_order().get_orderlines().find(l=>l.is_selected());
        this.env.pos.get_order()._resetLinePromotionPrograms(selected_line);
    }
}

ResetLinePromotionProgramsButton.template = 'ResetLinePromotionProgramsButton';

ProductScreen.addControlButton({
    component: ResetLinePromotionProgramsButton,
    condition: function () {
        return this.env.pos.promotionPrograms.length > 0;
    }
});

Registries.Component.add(ResetLinePromotionProgramsButton);
