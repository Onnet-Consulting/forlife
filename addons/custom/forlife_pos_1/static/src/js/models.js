odoo.define('pos_iot.models', function (require) {
    "use strict";

    var {PosGlobalState, register_payment_method} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosIotPosGlobalState = (PosGlobalState) => class PosIotPosGlobalState extends PosGlobalState {
        constructor() {
            super(...arguments);
        }

        async _processData(loadedData) {
            await super._processData(...arguments);
            this.partner_groups = loadedData['res.partner.group'];
        }
    }
    Registries.Model.extend(PosGlobalState, PosIotPosGlobalState);

});
