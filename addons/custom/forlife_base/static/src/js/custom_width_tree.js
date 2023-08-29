/** @odoo-module **/
import { ListRenderer } from "@web/views/list/list_renderer";
import { registry  } from "@web/core/registry";
const fieldRegistry = registry.category("fields");
import {patch} from "@web/core/utils/patch";

patch(ListRenderer.prototype, 'fixed_field_tree_one2many', {
    freezeColumnWidths() {
        if (!this.keepColumnWidths) {
            this.columnWidths = null;
        }

        const table = this.tableRef.el;
        const headers = [...table.querySelectorAll("thead th:not(.o_list_actions_header)")];

        if (!this.columnWidths || !this.columnWidths.length) {
            // no column widths to restore
            // Set table layout auto and remove inline style to make sure that css
            // rules apply (e.g. fixed width of record selector)
            table.style.tableLayout = "auto";
            headers.forEach((th) => {
                th.style.width = null;
                th.style.maxWidth = null;
            });

            this.setDefaultColumnWidths();

            // Squeeze the table by applying a max-width on largest columns to
            // ensure that it doesn't overflow
            this.columnWidths = this.computeColumnWidthsFromContent();
            table.style.tableLayout = "fixed";
        }
        headers.forEach((th, index) => {
            const field_name = th.getAttribute('data-name')
            const field = this.allColumns.find(field => field.name === field_name);
            if (field && field.rawAttrs && field.rawAttrs.x_width) {
                th.style.width = field.rawAttrs.x_width;
            }
            if (!th.style.width) {
                th.style.width = `${Math.floor(this.columnWidths[index])}px`;
            }
        });
    }
})