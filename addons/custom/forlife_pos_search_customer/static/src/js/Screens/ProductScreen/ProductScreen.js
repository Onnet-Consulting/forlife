odoo.define('forlife_pos_search_customer.CustomProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const CustomProductScreen = ProductScreen => class extends ProductScreen {

        async _barcodePartnerAction(code) {
            let parsed_code = this.parse_partner_app_barcode(code.base_code);
            if (!parsed_code) {
                return this.show_barcode_partner_error(code);
            }
            code.code = parsed_code;
            await this.get_partner_by_barcode_from_backend(code.code);
            return super._barcodePartnerAction(...arguments);
        }
    }

    Registries.Component.extend(ProductScreen, CustomProductScreen);

    return CustomProductScreen;

})