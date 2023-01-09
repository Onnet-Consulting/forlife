/** @odoo-module */
import {useService} from "@web/core/utils/hooks";

const {Component, onWillStart} = owl;

export class PosDashBoard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        onWillStart(async () => {
            this.posData = await this.orm.call(
                "store",
                "retrieve_dashboard",
            );
        });
    }
}

PosDashBoard.template = 'forlife_point_of_sale.PosDashboard'
