/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class EnterCodeButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        let { confirmed, payload: code } = await this.showPopup('TextInputPopup', {
            title: this.env._t('Enter Code'),
            startingValue: '',
            placeholder: this.env._t('Ex: FORMAT-001'),
        });
        if (confirmed) {
            code = code.trim();
            if (code !== '') {
                this.env.pos.get_order().activatePromotionCode(code);
            };
        }
    }
}

EnterCodeButton.template = 'EnterCodeButton';


ProductScreen.addControlButton({
    component: EnterCodeButton,
    condition: function () {
        return this.env.pos.promotionPrograms.some(
        p => p.promotion_type == 'code' || p.with_code == true);
    }
});

Registries.Component.add(EnterCodeButton);
