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

        get_install_app_barcode_data(json) {
            // if customer doesn't have barcode yet -> they have not install mobile app
            const mobile_app_url = this.pos.pos_brand_info.mobile_app_url;
            if (this.get_partner() && !this.get_partner().barcode && mobile_app_url) {
                let redirect_url = this.pos.base_url + '/pos/point/compensate?';
                redirect_url += `reference=${json.name}&redirect_url=${mobile_app_url}`
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(redirect_url, 150, 150));
                return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
            } else {
                return false;
            }
        }

        receipt_order_get_activated_code_by_id() {
            let order_activated_codes_arr = this.activatedInputCodes;
            if (!order_activated_codes_arr || order_activated_codes_arr.length === 0) return {};
            return order_activated_codes_arr.reduce((acc, obj) => {
                acc[obj.id] = obj.code;
                return acc;
            }, {})
        }

        receipt_order_get_applied_voucher_values() {
            let exist_voucher_payment = _.any(this.payment_lines, p => p.payment_method.is_voucher);
            let vouchers = this.data_voucher;
            if (exist_voucher_payment && vouchers && vouchers.length > 0) {
                let voucher_data = [];
                for (const voucher of vouchers) {
                    if (!voucher || !voucher.value) continue;
                    voucher_data.push({
                        "code": voucher.value.voucher_name,
                        "value": voucher.value.price_residual_no_compute
                    })
                }
                return voucher_data;
            }
            return false;
        }

        receipt_merge_line_same_product_and_price(lines) {
            let merge_line_values = {};
            for (const line of lines) {
                let product_id = line.get_product().id;
                let price = line.original_price;
                let qty = line.get_quantity();
                let product_default_code = line.get_product().default_code || '';
                let discount_amount = line.get_line_receipt_total_discount();
                let total_amount = line.get_display_price_after_discount();
                let total_original_amount = price * qty;
                if (!(product_id in merge_line_values)) {
                    merge_line_values[product_id] = {
                        'quantity': qty,
                        'product_default_code': product_default_code,
                        'original_price': price,
                        'discount_amount': discount_amount,
                        'total_amount': total_amount,
                        'id': line.id,
                        'product_name_wrapped': line.generate_wrapped_product_name(),
                        'total_original_amount': total_original_amount
                    }
                } else {
                    merge_line_values[product_id]['quantity'] += qty;
                    merge_line_values[product_id]['discount_amount'] += discount_amount;
                    merge_line_values[product_id]['total_amount'] += total_amount;
                    merge_line_values[product_id]['total_original_amount'] += total_original_amount
                }
            }
            for (let [product_id, value] of Object.entries(merge_line_values)) {
                value['discount_percent'] = parseInt(value['total_original_amount'] ? (value['discount_amount'] / value['total_original_amount']) * 100 : 0);
            }
            return Object.values(merge_line_values);
        }

        receipt_group_order_lines_by_promotion() {
            let promotion_lines = [];
            let lines_by_promotion_programs = {};
            let normal_lines = [];
            let applied_point_lines = [];
            let total_applied_points = 0;
            let order_activated_code_by_id = this.receipt_order_get_activated_code_by_id();
            let applied_code_value = {};
            let order_total_discount = 0;
            let order_total = 0;
            for (const line of this.get_orderlines()) {
                let {promotion_usage_ids, point, original_price} = line;
                let line_quantity = line.get_quantity();
                order_total_discount += line.get_line_receipt_total_discount()
                order_total += line.get_line_receipt_total_amount();
                if (point && point !== 0) {
                    applied_point_lines.push(line);
                    total_applied_points += Math.abs(point);
                    continue;
                }
                if (!promotion_usage_ids || promotion_usage_ids.length === 0) {
                    normal_lines.push(line);
                    continue;
                }
                let promotion_program_ids = [];
                for (const pro_line of promotion_usage_ids) {
                    let program_id = pro_line.program_id;
                    let program = this.pos.promotion_program_by_id[program_id];
                    promotion_program_ids.push(pro_line.program_id);
                    let code_id = pro_line.code_id;
                    if (code_id && order_activated_code_by_id[code_id]) {
                        let code = order_activated_code_by_id[code_id];
                        let code_amount = 0;
                        if (program.promotion_type === 'code') {
                            code_amount = pro_line.discount_amount * line_quantity;
                        }
                        if (!applied_code_value[code]) {
                            applied_code_value[code] = code_amount
                        } else {
                            applied_code_value[code] += code_amount
                        }
                    }

                }
                promotion_program_ids = _.sortBy(promotion_program_ids, num => num);
                let key_promotion_program_ids = JSON.stringify(promotion_program_ids);
                if (key_promotion_program_ids in lines_by_promotion_programs) {
                    lines_by_promotion_programs[key_promotion_program_ids].push(line)
                } else {
                    lines_by_promotion_programs[key_promotion_program_ids] = [line];
                }
            }

            for (const [program_ids, lines] of Object.entries(lines_by_promotion_programs)) {
                let raw_program_ids = JSON.parse(program_ids);
                let promotion_names = _.map(raw_program_ids, program_id => {
                    let program = this.pos.promotion_program_by_id[program_id];
                    if (program.promotion_type === 'pricelist' || program.program_type === 'pricelist') {
                        return false;
                    }
                    return program.name;
                })
                promotion_names = _.filter(promotion_names, name => name);
                promotion_lines.push({
                    "promotion_names": promotion_names,
                    "lines": this.receipt_merge_line_same_product_and_price(lines)
                })
            }

            let voucher_data = this.receipt_order_get_applied_voucher_values();

            normal_lines = this.receipt_merge_line_same_product_and_price(normal_lines);
            applied_point_lines = this.receipt_merge_line_same_product_and_price(applied_point_lines);

            return [normal_lines, promotion_lines, applied_point_lines, applied_code_value,
                order_total, order_total_discount, total_applied_points, voucher_data];
        }

        export_for_printing() {
            let json = super.export_for_printing(...arguments);
            let total_qty = _.reduce(_.map(json.orderlines, line => line.quantity), (a, b) => a + b, 0);
            json.date.localestring1 = json.date.localestring.replace(/\d{4}/, ('' + json.date.year).substring(2)).replace(/:\d{2}$/, '');
            json.total_line_qty = total_qty;
            json.footer = markup(this.pos.pos_brand_info.pos_receipt_footer);
            json.note = this.get_note();
            json.mobile_app_url_qr_code = this.get_install_app_barcode_data(json);
            let normal_lines, promotion_lines, applied_point_lines, applied_code_value, order_total,
                order_total_discount, total_applied_points, voucher_data;
            [normal_lines, promotion_lines, applied_point_lines, applied_code_value, order_total, order_total_discount, total_applied_points, voucher_data] = this.receipt_group_order_lines_by_promotion();
            json.normal_lines = normal_lines;
            json.promotion_lines = promotion_lines;
            json.applied_point_lines = applied_point_lines;
            json.order_total_discount = order_total_discount;
            json.order_total = order_total;
            json.applied_code_value = applied_code_value;
            json.voucher_data = voucher_data;
            json.total_applied_points = total_applied_points;
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
            let unit_price = this.original_price;
            let quantity = this.get_quantity();
            if (unit_price !== 0 && quantity !== 0) {
                percent_discount = ((discount / quantity) / unit_price) * 100;
            }
            return parseInt(percent_discount);
        }

        get_line_receipt_total_amount() {
            let line_quantity = this.get_quantity();
            let total = this.original_price * line_quantity;
            if (line_quantity < 0) {
                total -= this.get_line_receipt_total_discount();
            }
            return total;
        }

        export_for_printing() {
            let json = super.export_for_printing(...arguments);

            return _.extend(json, {
                product_default_code: this.get_product().default_code || '',
                original_price: this.original_price,
                discount_amount: this.get_line_receipt_total_discount(),
                discount_percent: this.get_line_receipt_total_percent_discount(),
                total_amount: this.get_display_price_after_discount()
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
