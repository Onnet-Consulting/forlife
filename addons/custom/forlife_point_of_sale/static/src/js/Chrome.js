odoo.define('forlife_point_of_sale.Chrome', function (require) {
    "use strict";
    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    let rpc = require('web.rpc');
    const PosChrome = (Chrome) =>
        class extends Chrome {
            _onBeforeUnload(event) {
                super._onBeforeUnload();
                this.showPopup('PosOpenedPopup');
                return event.returnValue = 'Confirm';
            }
        };

    Registries.Component.extend(Chrome, PosChrome);

    return Chrome;
});