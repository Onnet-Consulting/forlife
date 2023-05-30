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
            if (this.get_partner() && !this.get_partner().barcode && mobile_app_url) {
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(mobile_app_url, 150, 150));
                return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
            } else {
                return false;
            }
        }

        // FIXME: group promotion by program

        receipt_group_order_lines_by_promotion() {
            let promotion_lines_data = [];
            let lines_by_promotion_programs = {};
            let normal_lines = []
            for (const line of this.get_orderlines()) {
                let {promotion_usage_ids} = line;
                if (!promotion_usage_ids || promotion_usage_ids.length === 0) {
                    normal_lines.push(line);
                    continue;
                }
                let promotion_program_ids = _.sortBy(_.map(promotion_usage_ids, pro => pro.program_id), num => num);
                let key_promotion_program_ids = JSON.stringify(promotion_program_ids);
                if (key_promotion_program_ids in lines_by_promotion_programs) {
                    lines_by_promotion_programs[key_promotion_program_ids].push(line)
                } else {
                    lines_by_promotion_programs[key_promotion_program_ids] = [line];
                }
            }

            for (const [program_ids, lines] of Object.entries(lines_by_promotion_programs)) {
                let raw_program_ids = JSON.parse(program_ids);
                promotion_lines_data.push({
                    "promotion_names": _.map(raw_program_ids, program_id => this.pos.promotion_program_by_id[program_id].name),
                    "lines": _.map(lines, line => line.export_for_printing())
                })
            }

            return [normal_lines, promotion_lines_data];

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

        get_line_receipt_total_discount() {
            let total = 0;
            // used point
            if (this.point) {
                total += Math.abs(this.point);
            }
            // card rank
            total += this.get_card_rank_discount();
            if (this.money_reduce_from_product_defective > 0) {
                total += this.money_reduce_from_product_defective
            }
            // promotion
            const applied_promotions = this.get_applied_promotion_str();
            for (const applied_promotion of applied_promotions) {
                if (applied_promotion) {
                    total += applied_promotion.discount_amount;
                }
            }

            return total;
        }

        get_line_receipt_total_percent_discount() {
            let percent_discount = 0;
            let discount = this.get_line_receipt_total_discount();
            let unit_price = this.get_unit_display_price();
            let quantity = this.get_quantity();
            if (unit_price !== 0 && quantity !== 0) {
                percent_discount = ((discount / quantity) / unit_price) * 100;
            }
            return Math.round(percent_discount * 100) / 100;
        }

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
