odoo.define('forlife_point_of_sale.Chrome', function (require) {
    "use strict";
    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const PosChrome = (Chrome) =>
        class extends Chrome {
            _onBeforeUnload() {
                super._onBeforeUnload();
                return event.returnValue = 'Confirm';
            }
        };

    Registries.Component.extend(Chrome, PosChrome);

    return Chrome;
});