odoo.define('forlife_pos_layout.models', function (require) {
    "use strict";

    const {PosGlobalState, Orderline, Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const utils = require('web.utils')

    const round_pr = utils.round_precision;
    const LayoutOrderline = (Orderline) => class extends Orderline {
        constructor(obj, options) {
            super(...arguments);
            this.use_discount_cash = this.use_discount_cash || false
            this.discount_cash_amount = this.discount_cash_amount || 0
            console.log(options, 'options')
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.use_discount_cash = this.use_discount_cash;
            json.discount_cash_amount = this.discount_cash_amount;
            return json;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.use_discount_cash = json.use_discount_cash;
            this.discount_cash_amount = json.discount_cash_amount;

        }

        get_display_price_after_discount() {
            if (this.use_discount_cash) {
                return this.get_unit_price() - this.get_discount_cash_amount();
            }
            return this.get_display_price();
        }

        get_discount_cash_amount() {
            return this.discount_cash_amount;
        }

        set_discount_cash_manual(val) {
            const price = this.get_unit_price();
            const value = parseFloat(val)
            const rounding = this.pos.currency.rounding;
            const discount = round_pr((value / price) * 100, rounding);
            this.use_discount_cash = val > 0;
            this.discount_cash_amount = value;
            this.set_discount(discount);
        }

        get_all_prices(qty = this.get_quantity()) {
            var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
            if (this.use_discount_cash) {
                price_unit = this.get_unit_price() - this.get_discount_cash_amount();
            }
            var taxtotal = 0;

            var product = this.get_product();
            var taxes_ids = this.tax_ids || product.taxes_id;
            taxes_ids = _.filter(taxes_ids, t => t in this.pos.taxes_by_id);
            var taxdetail = {};
            var product_taxes = this.pos.get_taxes_after_fp(taxes_ids, this.order.fiscal_position);

            var all_taxes = this.compute_all(product_taxes, price_unit, qty, this.pos.currency.rounding);
            var all_taxes_before_discount = this.compute_all(product_taxes, this.get_unit_price(), qty, this.pos.currency.rounding);
            _(all_taxes.taxes).each(function (tax) {
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
            });

            return {
                "priceWithTax": all_taxes.total_included,
                "priceWithoutTax": all_taxes.total_excluded,
                "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
                "tax": taxtotal,
                "taxDetails": taxdetail,
            };
        }
    }

    Registries.Model.extend(Orderline, LayoutOrderline);
});