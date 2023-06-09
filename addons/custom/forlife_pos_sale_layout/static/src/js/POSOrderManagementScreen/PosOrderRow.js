odoo.define('forlife_pos_sale_layout.POSOrderRow', function(require) {
    'use strict';

    const POSOrderRow = require('forlife_pos_payment_change.POSOrderRow');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");

    const PosOrderRowShowInfo = POSOrderRow => class extends POSOrderRow {
        setup() {
            super.setup();
            useListener('pos-sale-detail', this._onShowPosSaleDetail);
        }

        async _onShowPosSaleDetail({ detail: order }) {
            const order_id = order.id;
            var order_lines = await this.rpc({
                model: 'pos.order.line',
                method: 'get_order_line',
                args: [order_id],
                context: this.env.session.user_context,
            });
            this.showPopup('PosOrderSaleInfoPopup', { orderline: order_lines});
        }

    }
    Registries.Component.extend(POSOrderRow, PosOrderRowShowInfo);

    return POSOrderRow;
});
