odoo.define('forlife_pos_app_member.CustomPartnerDetailsEdit', function (require) {
    const PartnerDetailsEdit = require('point_of_sale.PartnerDetailsEdit');
    const Registries = require('point_of_sale.Registries');
    const {useState, useRef} = owl;
    const {useListener} = require("@web/core/utils/hooks");


    const CustomPartnerDetailsEdit = PartnerDetailsEdit => class extends PartnerDetailsEdit {
        setup() {
            super.setup();
            this.changes['group_id'] = this.env.pos.default_partner_group.id;
            this.changes['retail_type_ids'] = [[4, this.env.pos.default_partner_retail_type_id]];
        }

        saveChanges() {
            super.saveChanges();
        }

    }

    Registries.Component.extend(PartnerDetailsEdit, CustomPartnerDetailsEdit);

    return CustomPartnerDetailsEdit;
})
