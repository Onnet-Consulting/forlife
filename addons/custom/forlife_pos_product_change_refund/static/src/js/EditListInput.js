/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import EditListInput from 'point_of_sale.EditListInput';


patch(EditListInput.prototype, "confirm_product_change_refund", {
    onKeyup(event) {
        if (event.key === "Enter" && event.target.value.trim() !== '') {
            this.trigger('create-new-item');
        }
        if (event.key === "F9" && event.target.value.trim() !== '') {
            this.trigger('confirm-item');
        }
    }
});