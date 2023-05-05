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
            this.changes['job_ids'] = [6, 0, this.env.pos.list_job_ids];
        }

        saveChanges() {
            var self = this
            this.env.pos.list_job_ids = []
            $('.o_input_job').each(function( index ) {
                if($(this).is(":checked")){
                    self.env.pos.list_job_ids.push(parseInt($(this).val()))
                }
            });
            this.changes['job_ids'] = this.env.pos.list_job_ids;
            return super.saveChanges();
        }
    }

    Registries.Component.extend(PartnerDetailsEdit, CustomPartnerDetailsEdit);

    return CustomPartnerDetailsEdit;
})
