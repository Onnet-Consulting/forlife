odoo.define('forlife_pos_app_member.CustomProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const CustomProductScreen = ProductScreen => class extends ProductScreen {
        // get UTC+7 (Asia/Ho_Chi_Minh) time
        get_current_vn_time() {
            let current_date = new Date();
            let utc_hour = current_date.getUTCHours();
            let utc_minute = current_date.getUTCMinutes();
            let vn_hour = (utc_hour + 7) % 24;
            return (vn_hour + '').padStart(2, '0') + (utc_minute + '').padStart(2, '0')
        }

        parse_partner_app_barcode(base_code) {
            let input_base_code = base_code;
            input_base_code = input_base_code.slice(1);
            let time_position = parseInt(input_base_code.slice(-2));
            input_base_code = input_base_code.slice(0, -2);
            let time_str = input_base_code.slice(time_position, time_position+4);
            input_base_code = input_base_code.slice(0, time_position) + input_base_code.slice(time_position+4)
            let current_vn_time = this.get_current_vn_time();
            if (current_vn_time > time_str){
                return false;
            }
            return input_base_code;
        }

        _barcodePartnerAction(code) {
            let new_code = this.parse_partner_app_barcode(code.base_code);
            if (!new_code){
                this._barcodeErrorAction(code);
                return false
            }
            code.code = new_code;
            return super._barcodePartnerAction(code);
        }
    }

    Registries.Component.extend(ProductScreen, CustomProductScreen);

    return CustomProductScreen;

})