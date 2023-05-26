odoo.define('forlife_pos_print_receipt.models', function (require) {
    let {Order, Orderline, PosGlobalState} = require('point_of_sale.models');
    let core = require('web.core');
    const Registries = require('point_of_sale.Registries');
    const {markup} = require("@odoo/owl");


    const ReceiptOrder = (Order) => class ReceiptOrder extends Order {
        constructor(obj, options) {
            super(...arguments);
            this.note = this.note || '';
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.note = json.note;
        }

        get_note() {
            return this.note;
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.note = this.note;
            return json;
        }

        set_note(note) {
            this.note = note;
        }

        get_install_app_barcode_data() {
            // if customer doesn't have barcode yet -> they have not install mobile app
            const mobile_app_url = this.pos.pos_brand_info.mobile_app_url;
            if (this.get_partner() && ! this.get_partner().barcode && mobile_app_url) {
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(mobile_app_url, 150, 150));
                return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
            } else {
                return false;
            }
        }

        receipt_group_order_lines_by_promotion(order_lines){
            let line_group_by_promotion_info = {};
            let normal_lines = []
            for (const line of order_lines){
                let {quantity, product, promotion_usage_ids} = line;
                let product_id = product.id;
                if (!promotion_usage_ids) {
                    normal_lines.push(line);
                    continue;
                }
                let product_key = "".concat(product_id, "_", quantity);
                for (const pro_line of promotion_usage_ids){
                    let {program_id, pro_priceitem_id, discount_amount} = pro_line;
                    // don't group line discounted by pricelist
                    if (!pro_priceitem_id) continue;
                    if (!(program_id in line_group_by_promotion_info)){
                        line_group_by_promotion_info[program_id] = {}
                    }
                    if (!(product_key in line_group_by_promotion_info[program_id])){
                        line_group_by_promotion_info[program_id][product_key] = {
                            "discount_amount":discount_amount
                        }
                    }
                    else{
                        // let exist_discount_amount = line_group_by_promotion_info[program_id][product_key]['discount_amount']
                        // if (exist_discount_amount === discount_amount){
                        //     line_group_by_promotion_info[program_id][product_key]['discount_amount'] = exist_discount_amount*2
                        // }
                        // let exist_quantity = product_promotion_info['quantity'];
                        // let exist_discount_amount = product_promotion_info['discount_amount'];

                    }
                    line_group_by_promotion_info[program_id] = {
                        product_id,
                        quantity,
                        discount_amount
                    }
                }
            }
        }

        export_for_printing() {
            let json = super.export_for_printing(...arguments);
            let total_qty = _.reduce(_.map(json.orderlines, line => line.quantity), (a, b) => a + b, 0);
            json.date.localestring1 = json.date.localestring.replace(/\d{4}/, ('' + json.date.year).substring(2)).replace(/:\d{2}$/, '');
            json.total_line_qty = total_qty;
            json.footer = markup(this.pos.pos_brand_info.pos_receipt_footer);
            json.note = this.get_note();
            json.mobile_app_url_qr_code = this.get_install_app_barcode_data();
            return json;
        }
    }

    const ReceiptOrderLine = (Orderline) => class ReceiptOrderLine extends Orderline {
        export_for_printing() {
            let json = super.export_for_printing(...arguments);

            return _.extend(json, {
                product_default_code: this.get_product().default_code || '',
            });
        }
    }

    const CustomPosGlobalState = PosGlobalState => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.pos_store_info = loadedData['pos_store_info'];
        }
    }

    Registries.Model.extend(Orderline, ReceiptOrderLine);
    Registries.Model.extend(Order, ReceiptOrder);
    Registries.Model.extend(PosGlobalState, CustomPosGlobalState);

});
