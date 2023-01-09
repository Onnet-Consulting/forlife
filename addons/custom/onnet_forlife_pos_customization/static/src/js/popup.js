odoo.define('onnet_forlife_pos_customization.popupcustomize', function (require) {
"use strict";

    const { PosGlobalState, Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const PosGlobalStateCustomize = (PosGlobalState) => class PosGlobalStateCustomize extends PosGlobalState {
//      @override
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.bank_statement = loadedData['account.bank.statement.line'];
            this.pos_customizes = loadedData['pos.customize'];
        }
    }
Registries.Model.extend(PosGlobalState, PosGlobalStateCustomize);
});