/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";
import { Gui } from 'point_of_sale.Gui';
import core from 'web.core';
const _t = core._t;

export class ResetLinePromotionProgramsButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        let selected_line = this.env.pos.get_order().get_orderlines().find(l=>l.is_selected());
        if (selected_line) {
            this.env.pos.get_order()._resetLinePromotionPrograms(selected_line);
        } else {
            Gui.showNotification(_t(`Vui lòng chọn một dòng đơn hàng để đặt lại CTKM.`), 3000);
        }
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
