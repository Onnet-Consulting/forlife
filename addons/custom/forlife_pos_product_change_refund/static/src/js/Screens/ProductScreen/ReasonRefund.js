odoo.define('forlife_pos_product_change_refund.ReasonRefund', function (require) {
    "use strict"

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');


    class PosReasonRefund extends PosComponent {

        selectReason(event) {
            const $select = $(event.target);
            if (parseInt($select.value) !== 0) {
                this.props.order_line.reason_refund_id = parseInt($select[0].value)
            }
        }

    }

    PosReasonRefund.template = 'PosReasonRefund';

    Registries.Component.add(PosReasonRefund);

    return PosReasonRefund;

});
