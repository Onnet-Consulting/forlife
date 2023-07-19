/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import {Order, Orderline, PosGlobalState} from 'point_of_sale.models';

patch(PosGlobalState.prototype, "rewrite_flush_orders", {
    _flush_orders(orders, options) {
        var self = this;

        return this._save_to_server(orders, options).then(function (server_ids) {
            for (let i = 0; i < server_ids.length; i++) {
                self.validated_orders_name_server_id_map[server_ids[i].pos_reference] = server_ids[i].id;
                self.sum_total_point = server_ids[i].sum_total_point
                self.total_point = server_ids[i].total_point
            }
            return server_ids;
        }).finally(function () {
            self._after_flush_orders(orders);
        });
    }
});