/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";


patch(Many2OneField, "Many2OneField_Disable_Quick_Create", {
    extractProps: ({attrs, field}) => {
        const noOpen = Boolean(attrs.options.no_open);
        const noCreate = true;
        const canCreate = false;
        const canWrite = attrs.can_write && Boolean(JSON.parse(attrs.can_write));
        const noQuickCreate = true;
        const noCreateEdit = true;
        const canScanBarcode = Boolean(attrs.options.can_scan_barcode);

        return {
            placeholder: attrs.placeholder,
            canOpen: !noOpen,
            canCreate,
            canWrite,
            canQuickCreate: canCreate && !noQuickCreate,
            canCreateEdit: canCreate && !noCreateEdit,
            relation: field.relation,
            string: attrs.string || field.string,
            nameCreateField: attrs.options.create_name_field,
            canScanBarcode: canScanBarcode,
            openTarget: attrs.open_target,
        };
    }
});