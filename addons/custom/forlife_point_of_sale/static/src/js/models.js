odoo.define('forlife_point_of_sale.models', function (require) {
    "use strict";

    var {PosGlobalState} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const CustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.pos_brand_id = loadedData['pos_brand_id'];
        }
    }
    Registries.Model.extend(PosGlobalState, CustomPosGlobalState);

});
