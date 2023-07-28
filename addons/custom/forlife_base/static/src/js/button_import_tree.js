/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import {ListController} from "@web/views/list/list_controller";
import {useService} from "@web/core/utils/hooks";
const { useRef} = owl;

patch(ListController.prototype, "list_controller_import", {
    setup() {
        this._super.apply();
        this.action = useService("action")
        this.actionRef = useRef("action");
    },
    buttonImport() {
        const $el = $(this.actionRef.el)
        const action = $el.attr('action')
        this.action.doAction(action)
    }
});