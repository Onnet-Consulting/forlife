/** @odoo-module **/

import PartnerDetailsEdit from 'point_of_sale.PartnerDetailsEdit';
import Registries from 'point_of_sale.Registries';

export const CustomPartnerDetailsEdit = (PartnerDetailsEdit) =>
    class extends PartnerDetailsEdit {
        setup() {
            super.setup();
            this.changes['group_id'] = this.env.pos.default_partner_group.id;
            this.changes['retail_type_ids'] = [[4, this.env.pos.default_partner_retail_type_id]];
        }

        saveChanges() {
            super.saveChanges();
        }
    };
Registries.Component.extend(PartnerDetailsEdit, CustomPartnerDetailsEdit);
