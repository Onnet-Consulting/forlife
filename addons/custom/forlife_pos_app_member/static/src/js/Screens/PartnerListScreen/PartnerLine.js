odoo.define('forlife_pos_app_member.PartnerLine', function (require) {
    'use strict';

    const PartnerLine = require('point_of_sale.PartnerLine');
    const Registries = require('point_of_sale.Registries');

    const PosPartnerLine = (PartnerLine) =>
        class extends PartnerLine {
            _getPartnerType() {
               var string = '';
               var self = this;
               for(let i=0; i< self.env.pos.partner_types.length;i++){
                    for(let j=0;j< self.props.partner.retail_type_ids.length;j++){
                        if(self.props.partner.retail_type_ids[j] == self.env.pos.partner_types[i].id){
                           string += `${self.env.pos.partner_types[i].name}, `
                        }
                    }
               }
               return string.replace(/, *$/, '');
            }
        };

    Registries.Component.extend(PartnerLine, PosPartnerLine);

    return PartnerLine;
});
