/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import * as debugs from "@web/core/debug/debug_context";
import {useEffect, useEnv} from '@odoo/owl';
import {registry} from "@web/core/registry";

function useDebugCategoryCustom(category, context = {}) {
    const env = useEnv();

    if (env.searchModel && !env.searchModel._context.debug) {
        return;
    }

    if (env.debug) {
        const debugContext = useEnvDebugContext();
        if (debugContext) {
            useEffect(
                () => debugContext.activateCategory(category, context),
                () => []
            );
        }
    }
}

patch(debugs, 'forlife_pos_product_change_refund.newDebug', {
    useDebugCategory(category, context = {}) {
        return useDebugCategoryCustom(category, context = {})
    }
})

registry.category("debug").category("view").add("debugCustom", useDebugCategoryCustom);
