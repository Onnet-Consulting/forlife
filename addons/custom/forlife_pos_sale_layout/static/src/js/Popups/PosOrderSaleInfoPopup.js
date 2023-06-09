odoo.define('forlife_pos_sale_layout.PosOrderSaleInfoPopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');


    class PosOrderSaleInfoPopup extends AbstractAwaitablePopup {}

    PosOrderSaleInfoPopup.template = "PosOrderSaleInfoPopup";
    PosOrderSaleInfoPopup.defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Order Detail")
    };
    Registries.Component.add(PosOrderSaleInfoPopup);

    return PosOrderSaleInfoPopup;
})