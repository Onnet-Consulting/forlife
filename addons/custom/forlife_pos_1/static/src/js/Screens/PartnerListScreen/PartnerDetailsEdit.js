odoo.define('forlife_pos_1.PartnerDetailsEdit', function (require) {
    'use strict';
    const PartnerDetailsEdit = require('point_of_sale.PartnerDetailsEdit');
    const Registries = require('point_of_sale.Registries');

    const CustomPartnerDetailsEdit = PartnerDetailsEdit =>
        class extends PartnerDetailsEdit {
            super() {
                super.setup();
                this.changes['group_id'] = this.env.pos.default_partner_group.id;
                this.changes['retail_type_ids'] = [[4, this.env.pos.default_partner_retail_type_id]];
            }
        }

    Registries.Component.extend(PartnerDetailsEdit, CustomPartnerDetailsEdit);
    return PartnerDetailsEdit;
})
