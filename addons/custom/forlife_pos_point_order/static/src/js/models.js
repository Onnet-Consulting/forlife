odoo.define('forlife_pos_point_order.models', function (require) {
    "use strict";

    var {PosGlobalState, Orderline, Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;
    const PointsOrderLine = (Orderline) =>
        class extends Orderline {
            constructor(obj, options) {
                super(...arguments);
            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
                this.point = json.point;
            }

            clone() {
                let orderline = super.clone(...arguments);
                orderline.point = this.point;
                return orderline;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                json.point = this.point;
                return json;
            }

            set_point(point) {
                this.point = point ? parseInt(point) : null;
            }

            get_point() {
                return this.point;
            }

            get_price_point_tax(){
                return this.get_all_prices_of_point().total_point_after_Tax;
            }


            get_all_prices_of_point(qty = 1){
                var pointOfline = this.point ? parseInt(-this.point) : 0;
                var tax_point = 0;

                var product =  this.get_product();
                var taxes_ids = this.tax_ids || product.taxes_id;
                taxes_ids = _.filter(taxes_ids, t => t in this.pos.taxes_by_id);
                var product_taxes = this.pos.get_taxes_after_fp(taxes_ids, this.order.fiscal_position);

                var all_taxes_of_point = this.compute_all(product_taxes, pointOfline, qty, this.pos.currency.rounding);
                _(all_taxes_of_point.taxes).each(function(tax) {
                    tax_point += tax.amount;
                });

                return {
                    "total_point_after_Tax": parseInt(pointOfline) - tax_point
                };
            }

        };
    const PointsOrder = (Order) =>
        class extends Order {
            constructor(obj, options) {
                super(...arguments);
            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
            }

            clone() {
                let order = super.clone(...arguments);
                return order;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                var total = this.get_total_with_tax();
                var totalWithoutTax = this.get_total_without_tax() - this.get_total_point_tax();
                var taxAmount = total - totalWithoutTax;
                json.amount_tax = taxAmount;
                return json;
            }
            get_total_with_tax() {
                var total = super.get_total_with_tax()
                var vals = 0
                for(let i =0; i<this.orderlines.length; i++){
                    if (this.orderlines[i].point){
                        vals += parseInt(this.orderlines[i].point)
                    }
                }
                return total + vals;
            }

            get_total_point_tax() {
                return round_pr(this.orderlines.reduce((function(sum, orderLine) {
                    return sum + orderLine.get_price_point_tax();
                }), 0), this.pos.currency.rounding);
            }

    }
    Registries.Model.extend(Orderline, PointsOrderLine);
    Registries.Model.extend(Order, PointsOrder);
});