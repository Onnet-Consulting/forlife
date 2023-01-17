odoo.define('forlife_pos_assign_employee.models', function (require) {
    "use strict";

    var {PosGlobalState} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosCustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.assignable_employees = loadedData['assignable_employees'];
        }
    }
    Registries.Model.extend(PosGlobalState, PosCustomPosGlobalState);

});
