/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useBarcodeReader } from 'point_of_sale.custom_hooks';

export const PosVoucherProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        async _onClickPay() {
            this.env.pos.selectedOrder.data_voucher = false;
            return super._onClickPay(...arguments);
        }
    };

Registries.Component.extend(ProductScreen, PosVoucherProductScreen);
