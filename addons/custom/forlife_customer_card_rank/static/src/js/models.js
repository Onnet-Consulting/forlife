odoo.define('forlife_customer_card_rank.models', function (require) {
    "use strict";

    var {PosGlobalState} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const CardRankPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.card_rank_program_by_rank_id = loadedData['card_rank_program_by_rank_id'];
            if (!this.pos_branch) {
                this.pos_branch = loadedData['pos.branch'];
            }
        }
    }
    Registries.Model.extend(PosGlobalState, CardRankPosGlobalState);

});
