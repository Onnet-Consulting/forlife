odoo.define('forlife_pos_promotion.models', function (require) {
    "use strict";

    var {PosGlobalState, register_payment_method} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosCustomPosGlobalState = (PosGlobalState) => class extends PosGlobalState {
            async load_new_partners_customize(id){
                let search_params = { domain: [['id','=', id]] }
                let partners = await this.env.services.rpc({
                    model: 'pos.session',
                    method: 'get_pos_ui_res_partner_by_params',
                    args: [[odoo.pos_session_id], search_params],
                }, {
                    timeout: 3000,
                    shadow: true,
                })
                if (this.addPartners(partners)){
                    return true
                }
                else{
                    return false
                }
            }
    }
    Registries.Model.extend(PosGlobalState, PosCustomPosGlobalState);

});
