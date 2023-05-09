odoo.define('forlife_pos_print_receipt.models', function (require) {
    let {Order, Orderline} = require('point_of_sale.models');
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

        export_for_printing() {
            let json = super.export_for_printing(...arguments);
            let total_qty = _.reduce(_.map(json.orderlines, line => line.quantity), (a, b) => a + b, 0);
            json.date.localestring1 = json.date.localestring.replace(/\d{4}/, ('' + json.date.year).substring(2)).replace(/:\d{2}$/, '');
            json.total_line_qty = total_qty;
            json.footer = markup(this.pos.pos_brand_info.pos_receipt_footer);
            json.note = this.get_note();
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
    Registries.Model.extend(Orderline, ReceiptOrderLine);
    Registries.Model.extend(Order, ReceiptOrder);
});
