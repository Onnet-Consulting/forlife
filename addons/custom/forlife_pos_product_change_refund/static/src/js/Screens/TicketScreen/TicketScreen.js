odoo.define('forlife_pos_product_change_refund.TicketScreen', function (require) {
    'use strict';

    const { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const TicketScreen = require('point_of_sale.TicketScreen');

    const TicketScreenChangeRefund = TicketScreen => class extends TicketScreen {

        async _removeHandleChangeRefund(order) {
            for (const line of order.get_orderlines()) {
                if (line.handle_change_refund_id) {
                    var args = {};
                    args.id = line.handle_change_refund_id;
                    await this.rpc({
                        model: 'handle.change.refund',
                        method: 'cancel_rc_handle_change_refund',
                        args: [args],
                    })
                }
            }
        }

        async _onDeleteOrder({ detail: order }) {
            await super._onDeleteOrder(...arguments);
            const new_orders = this.env.pos.get_order_list();
            for (const new_order of new_orders) {
                if (new_order === order) {
                    return;
                }
            }
            this._removeHandleChangeRefund(order);
        }

        getTotal(order) {
            let total_reduce = 0
            order.orderlines.forEach(function(item){
                if(!item.is_promotion){
                   total_reduce += item.subtotal_paid
                }
            })
            return this.env.pos.format_currency(total_reduce);
        }
    };

    Registries.Component.extend(TicketScreen, TicketScreenChangeRefund);

    return TicketScreenChangeRefund;
});
