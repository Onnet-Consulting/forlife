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

        _setValue(val) {
            if (this.currentOrder.get_selected_orderline()) {
                if (this.env.pos.numpadMode === 'quantity') {
                    const result = this.currentOrder.get_selected_orderline().set_quantity(val);
                    if (!result) NumberBuffer.reset();
                } else if (this.env.pos.numpadMode === 'discount') {
                    this.currentOrder.get_selected_orderline().set_discount_cash_manual(0);
                    this.currentOrder.get_selected_orderline().set_discount(val);
                } else if (this.env.pos.numpadMode === 'price') {
                    var selected_orderline = this.currentOrder.get_selected_orderline();
                    // selected_orderline.price_manually_set = true;
                    // selected_orderline.set_unit_price(val);
                    selected_orderline.set_discount_cash_manual(val);
                }
            }
        }
    }

    Registries.Component.extend(ProductScreen, CustomProductScreen);

    return CustomProductScreen;

})
