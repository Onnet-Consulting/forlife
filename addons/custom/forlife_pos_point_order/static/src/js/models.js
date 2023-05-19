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
                this.is_new_line_point = this.is_new_line_point || false;
            }

//            set_quantity(quantity, keep_price){
//                this.order.old_data = false
//                for (let i = 0; i < this.order.orderlines.length; i++) {
//                    this.order.orderlines[i].point = false
//                    this.order.orderlines[i].is_new_line_point = false
//                }
//                return super.set_quantity(quantity, keep_price)
//            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
                this.point = json.point;
                this.is_new_line_point = json.is_new_line_point;
            }

            clone() {
                let orderline = super.clone(...arguments);
                orderline.point = this.point;
                orderline.is_new_line_point = this.is_new_line_point;
                return orderline;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                json.point = this.point;
                json.is_new_line_point = this.is_new_line_point;
                return json;
            }

            set_point(point) {
                this.point = point ? parseInt(point) : null;
            }

            get_point() {
                return this.point;
            }

            get_price_point_without_tax() {
                return this.get_all_prices_of_point().total_point_without_Tax;
            }

            get_display_price_after_discount() {
                var total = super.get_display_price_after_discount(...arguments);
                if (this.point) {
                    total += this.point;
                }
                return total;
            }


            get_all_prices_of_point(qty = 1) {
                var pointOfline = this.point ? parseInt(-this.point) : 0;
                var tax_point = 0;

                var product = this.get_product();
                var taxes_ids = this.tax_ids || product.taxes_id;
                taxes_ids = _.filter(taxes_ids, t => t in this.pos.taxes_by_id);
                var product_taxes = this.pos.get_taxes_after_fp(taxes_ids, this.order.fiscal_position);
                var number_tax = 0
                for (let i = 0; i < product_taxes.length; i++) {
                    number_tax += product_taxes[i].amount
                }
                var total_tax = 1 + number_tax / 100;
                var pointOflineBeforeTax = pointOfline / total_tax;
                var all_taxes_of_point = this.compute_all(product_taxes, pointOflineBeforeTax, qty, this.pos.currency.rounding);
                _(all_taxes_of_point.taxes).each(function (tax) {
                    tax_point += tax.amount;
                });

                return {
                    "total_point_without_Tax": parseInt(pointOfline) - tax_point
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
                this.total_order_line_point_used = json.total_order_line_point_used;
                this.total_order_line_redisual = json.total_order_line_redisual;
                this.allow_for_point = false;
            }

            clone() {
                let order = super.clone(...arguments);
                order.total_order_line_point_used = this.total_order_line_point_used;
                order.total_order_line_redisual = this.total_order_line_redisual;
                order.allow_for_point = false;
                return order;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                json.total_order_line_point_used = this.total_order_line_point_used;
                json.total_order_line_redisual = this.total_order_line_redisual;
                json.allow_for_point = this.allow_for_point;
                var total = this.get_total_with_tax();
                var totalWithoutTax = this.get_total_without_tax() - this.get_total_point_without_tax();
                var taxAmount = total - totalWithoutTax;
                json.amount_tax = taxAmount;
                return json;
            }

            get_total_with_tax() {
                var total = super.get_total_with_tax()
                var vals = 0
                for (let i = 0; i < this.orderlines.length; i++) {
                    if (this.orderlines[i].point) {
                        vals += parseInt(this.orderlines[i].point)
                    }
                }
                return total + vals;
            }

            get_total_point_without_tax() {
                return round_pr(this.orderlines.reduce((function (sum, orderLine) {
                    return sum + orderLine.get_price_point_without_tax();
                }), 0), this.pos.currency.rounding);
            }

            set_partner(partner) {
                super.set_partner(partner);
                this.allow_for_point = Boolean(partner && partner.generated_by_scan_barcode);
            }
            add_product(product, options){
                this.old_data = false;
                for (let i = 0; i < this.orderlines.length; i++) {
                     this.orderlines[i].point = false
                     this.orderlines[i].is_new_line_point = false
                }
                return super.add_product(product,options)
            }
            remove_orderline( line ){
                super.remove_orderline(line)
                this.old_data = false;
            }

            createNewLinePoint(line){
                  this.fix_tax_included_price(line);
                  this.add_orderline(line);
                  return line
            }
        }
    Registries.Model.extend(Orderline, PointsOrderLine);
    Registries.Model.extend(Order, PointsOrder);
});