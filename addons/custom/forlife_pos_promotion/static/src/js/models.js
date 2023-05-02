odoo.define('forlife_pos_promotion.models', function (require) {
    "use strict";

    var {PosGlobalState} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const LoadPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
        async loadPartnersBackground(domain=[], offset=0, order=false) {
        // Start at the first page since the first set of loaded partners are not actually in the
        // same order as this background loading procedure.
        let i = 0;
        let partners = [];
        do {
            partners = await this.env.services.rpc({
                model: 'pos.session',
                method: 'get_pos_ui_res_partner_by_params',
                args: [
                    [odoo.pos_session_id],
                    {
                        domain: domain,
                        limit: 1,
                        offset: offset + this.config.limited_partners_amount * i,
                        order: order,
                    },
                ],
                context: this.env.session.user_context,
            }, { shadow: true });
            this.addPartners(partners);
            i += 1;
        } while(partners.length);
    }

    }
    Registries.Model.extend(PosGlobalState, LoadPosGlobalState);

});
