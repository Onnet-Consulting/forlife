odoo.define('forlife_voucher.voucher', function (require) {
"use strict";

    const { PosGlobalState, Order} = require('point_of_sale.models');
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
    const PosGlobalStateVoucher = (PosGlobalState) => class PosGlobalStateVoucher extends PosGlobalState {
//      @override
        push_single_order (order, opts) {
            opts = opts || {};
            const self = this;

            const order_id = self.db.add_order(order.export_as_JSON());

            return new Promise((resolve, reject) => {
                this.env.posMutex.exec(async () => {
                    const order = self.db.get_order(order_id);
                    try {
                        resolve(await self._flush_orders([order], opts));
                    } catch (error) {
                        reject(error);
                    }
                });
            });
        }

    }
    const VoucherOrder = (Order) =>
        class extends Order {
            constructor(obj, options) {
                super(...arguments);
                this.voucherlines  = new PosCollection();
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

    }
Registries.Model.extend(Order, VoucherOrder);
Registries.Model.extend(PosGlobalState, PosGlobalStateVoucher);
});