odoo.define('forlife_pos_payment_change.POSOrderManagementControlPanel', function (require) {
    'use strict';

    const { useAutofocus, useListener } = require("@web/core/utils/hooks");
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const POSOrderFetcher = require('forlife_pos_payment_change.POSOrderFetcher');
    const contexts = require('point_of_sale.PosContext');

    const { useState } = owl;

    const VALID_SEARCH_TAGS = new Set(['date', 'customer', 'client', 'name', 'order']);
    const FIELD_MAP = {
        date: 'date_order',
        customer: 'partner_id.display_name',
        client: 'partner_id.display_name',
        name: 'name',
        order: 'name',
    };
    const SEARCH_FIELDS = ['name', 'partner_id.display_name', 'date_order'];

    /**
     * @emits close-screen
     * @emits prev-page
     * @emits next-page
     * @emits search
     */
    class POSOrderManagementControlPanel extends PosComponent {
        setup() {
            super.setup();
            this.orderManagementContext = useState(contexts.orderManagement);
            useListener('clear-search', this._onClearSearch);
            useAutofocus();

            let currentPartner = this.env.pos.get_order().get_partner();
            if (currentPartner) {
                this.orderManagementContext.searchString = currentPartner.name;
            }
//            POSOrderFetcher.setSearchDomain(this._computeDomain());
        }
//        onInputKeydown(event) {
//            if (event.key === 'Enter') {
//                this.trigger('search', this._computeDomain());
//            }
//        }
        get showPageControls() {
            return POSOrderFetcher.lastPage > 1;
        }
        get pageNumber() {
            const currentPage = POSOrderFetcher.currentPage;
            const lastPage = POSOrderFetcher.lastPage;
            return isNaN(lastPage) ? '' : `(${currentPage}/${lastPage})`;
        }
//        get validSearchTags() {
//            return VALID_SEARCH_TAGS;
//        }
//        get fieldMap() {
//            return FIELD_MAP;
//        }
//        get searchFields() {
//            return SEARCH_FIELDS;
//        }

//        _computeDomain() {
//            let domain = [['state', '!=', 'cancel'],['invoice_status', '!=', 'invoiced']];
//            const input = this.orderManagementContext.searchString.trim();
//            if (!input) return domain;
//
//            const searchConditions = this.orderManagementContext.searchString.split(/[,&]\s*/);
//            if (searchConditions.length === 1) {
//                let cond = searchConditions[0].split(/:\s*/);
//                if (cond.length === 1) {
//                  domain = domain.concat(Array(this.searchFields.length - 1).fill('|'));
//                  domain = domain.concat(this.searchFields.map((field) => [field, 'ilike', `%${cond[0]}%`]));
//                  return domain;
//                }
//            }
//
//            for (let cond of searchConditions) {
//                let [tag, value] = cond.split(/:\s*/);
//                if (!this.validSearchTags.has(tag)) continue;
//                domain.push([this.fieldMap[tag], 'ilike', `%${value}%`]);
//            }
//            return domain;
//        }
        _onClearSearch() {
            this.orderManagementContext.searchString = '';
            this.onInputKeydown({ key: 'Enter' });
        }
    }
    POSOrderManagementControlPanel.template = 'POSOrderManagementControlPanel';

    Registries.Component.add(POSOrderManagementControlPanel);

    return POSOrderManagementControlPanel;
});
