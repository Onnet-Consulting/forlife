odoo.define('forlife_pos_product_change_refund.PosOrderRefundDetailPopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');


    class PosOrderRefundDetailPopup extends AbstractAwaitablePopup {}

    PosOrderRefundDetailPopup.template = "PosOrderRefundDetailPopup";
    PosOrderRefundDetailPopup.defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Order Detail")
    };
    Registries.Component.add(PosOrderRefundDetailPopup);

    return PosOrderRefundDetailPopup;
})