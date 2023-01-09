/** @odoo-module **/

import {registry} from "@web/core/registry";
import {kanbanView} from '@web/views/kanban/kanban_view';
import {KanbanRenderer} from '@web/views/kanban/kanban_renderer';
import {PosDashBoard} from '@forlife_point_of_sale/views/pos_dashboard';


export class PosDashBoardKanbanRenderer extends KanbanRenderer {};

PosDashBoardKanbanRenderer.template = 'forlife_point_of_sale.PosKanbanView';
PosDashBoardKanbanRenderer.components = Object.assign({}, KanbanRenderer.components, {PosDashBoard})

export const PosDashBoardKanbanView = {
    ...kanbanView,
    Renderer: PosDashBoardKanbanRenderer,
};

registry.category("views").add("pos_dashboard_kanban", PosDashBoardKanbanView);