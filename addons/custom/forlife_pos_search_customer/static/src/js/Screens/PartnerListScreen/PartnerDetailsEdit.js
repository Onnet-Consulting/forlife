odoo.define('forlife_pos_search_customer.CustomPartnerDetailsEdit', function (require) {
    const PartnerDetailsEdit = require('point_of_sale.PartnerDetailsEdit');
    const Registries = require('point_of_sale.Registries');

    const CustomPartnerDetailsEdit = PartnerDetailsEdit => class extends PartnerDetailsEdit {
        setup() {
            super.setup();
            let new_fields = ['phone', 'name', 'email'];
            new_fields.forEach((field, i) => {
                if(this.props.partner[field]){
                    this.changes[field] = this.props.partner[field];
                }
            });
        }
    }

    Registries.Component.extend(PartnerDetailsEdit, CustomPartnerDetailsEdit);

    return CustomPartnerDetailsEdit;
})
