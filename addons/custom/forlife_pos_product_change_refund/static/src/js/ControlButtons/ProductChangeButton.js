/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class ProductChangeButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClickChangeProduct);
    }

    async onClickChangeProduct() {
        const { confirmed, payload: newOrder } = await this.showTempScreen(
            'OrderChangeRefundProductScreen',
            { order: [], is_change_product: true }
        );
    }
}

ProductChangeButton.template = 'ProductChangeButton';

ProductScreen.addControlButton({
    component: ProductChangeButton
});

Registries.Component.add(ProductChangeButton);
