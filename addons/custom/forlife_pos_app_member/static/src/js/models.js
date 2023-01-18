odoo.define('forlife_pos_app_member.models', function (require) {
    "use strict";

    var {PosGlobalState, register_payment_method} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosCustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.default_partner_group = loadedData['default_partner_group'];
            this.default_partner_retail_type_id = loadedData['default_partner_retail_type_id'];
        }
    }
    Registries.Model.extend(PosGlobalState, PosCustomPosGlobalState);

});
