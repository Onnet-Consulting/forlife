/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class ProductRefundButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClickRefundProduct);
    }

    async onClickRefundProduct() {
        const { confirmed, payload: newOrder } = await this.showTempScreen(
            'OrderChangeRefundProductScreen',
            { order: [], is_refund_product: true }
        );
    }
}

ProductRefundButton.template = 'ProductRefundButton';

ProductScreen.addControlButton({
    component: ProductRefundButton
});

Registries.Component.add(ProductRefundButton);
