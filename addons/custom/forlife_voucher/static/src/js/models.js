odoo.define('forlife_voucher.voucher', function (require) {
"use strict";

    const { PosGlobalState, Order, Orderline} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    class PosCollection extends Array {
        getByCID(cid) {
            return this.find(item => item.cid == cid);
        }
        add(item) {
            this.push(item);
        }
        remove(item) {
            const index = this.findIndex(_item => item.cid == _item.cid);
            if (index < 0) return index;
            this.splice(index, 1);
            return index;
        }
        reset() {
            this.length = 0;
        }
        at(index) {
            return this[index];
        }
    }
    const VoucherOrder = (Order) =>
        class extends Order {
            constructor(obj, options) {
                super(...arguments);
                this.voucherlines  = this.voucherlines || [];
            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
                this.voucherlines = json.voucherlines;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                json.voucherlines = this.voucherlines;
                return json;
            }

            addVoucherline(data) {
                var voucherLines = []
                for (let index = 0; index < data.length; index++) {
                    if (data[index].value != false) {
                        data[index].value.store_ids = false
                        voucherLines.push([0,0,data[index].value])
                    }
                }
                this.voucherlines = voucherLines
            }

            remove_all_paymentlines(){
                var self = this;
                for(let index = 0; index<2; index ++){
                    var lines = self.paymentlines;
                        for(let i = 0; i< lines.length; i++){
                            self.paymentlines.remove(lines[i])
                        }
                    }
            }
            set_partner(partner) {
                const oldPartner = this.get_partner();
                super.set_partner(partner);
                if (oldPartner !== this.get_partner()) {
                    this.remove_all_paymentlines()
                }
            };
            add_product(product, options){
                this.remove_all_paymentlines()
                return super.add_product(product,options)
            }


    };
    const PointsOrderLine = (Orderline) =>
        class extends Orderline {
            constructor(obj, options) {
                super(...arguments);
            }

            init_from_JSON(json) {
                super.init_from_JSON(...arguments);
                this.is_voucher_conditional = json.is_voucher_conditional;
            }

            clone() {
                let orderline = super.clone(...arguments);
                orderline.is_voucher_conditional = this.is_voucher_conditional;
                return orderline;
            }

            export_as_JSON() {
                const json = super.export_as_JSON(...arguments);
                json.is_voucher_conditional = this.is_voucher_conditional;
                return json;
            }
            remove_all_paymentlines(){
                var self = this;
                for(let index = 0; index<2; index ++){
                    var lines = self.order.paymentlines;
                        for(let i = 0; i< lines.length; i++){
                            self.order.paymentlines.remove(lines[i])
                        }
                    }
            }
            set_quantity(quantity, keep_price){
                this.remove_all_paymentlines()
                return super.set_quantity(quantity, keep_price)
            }

        };
Registries.Model.extend(Orderline, PointsOrderLine);
Registries.Model.extend(Order, VoucherOrder);
});