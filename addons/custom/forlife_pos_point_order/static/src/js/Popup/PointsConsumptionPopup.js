odoo.define('forlife_pos_point_order.PointsConsumptionPopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');


    class PointsConsumptionPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
        }

    }

    PointsConsumptionPopup.template = "PointsConsumptionPopup";
    PointsConsumptionPopup.defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Employee")
    };
    Registries.Component.add(PointsConsumptionPopup);

    return PointsConsumptionPopup;
})