odoo.define('forlife_pos_layout.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const CustomProductScreen = ProductScreen => class extends ProductScreen {
        // get UTC+7 (Asia/Ho_Chi_Minh) time
        async _barcodeProductAction(code) {
            let product = this.env.pos.db.get_product_by_barcode(code.base_code);
            if (!product) {
                return this._barcodeErrorAction(code);
            }
            const options = await this._getAddProductOptions(product, code);
            // Do not proceed on adding the product when no options is returned.
            // This is consistent with _clickProduct.
            if (!options) return;

            // update the options depending on the type of the scanned code
            if (code.type === 'price') {
                Object.assign(options, {
                    price: code.value,
                    extras: {
                        price_manually_set: true,
                    },
                });
            } else if (code.type === 'weight') {
                Object.assign(options, {
                    quantity: code.value,
                    merge: false,
                });
            } else if (code.type === 'discount') {
                Object.assign(options, {
                    discount: code.value,
                    merge: false,
                });
            }
            this.currentOrder.add_product(product,  options);
            NumberBuffer.reset();
        }
    }

    Registries.Component.extend(ProductScreen, CustomProductScreen);

    return CustomProductScreen;

})
