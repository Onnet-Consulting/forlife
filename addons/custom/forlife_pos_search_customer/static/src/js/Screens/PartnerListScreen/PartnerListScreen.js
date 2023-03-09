odoo.define('forlife_pos_search_customer.PartnerListScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");

    const PartnerListScreen = require('point_of_sale.PartnerListScreen');

    const SearchPartnerListScreen = PartnerListScreen => class extends PartnerListScreen {

        setup() {
            super.setup();
            useListener('search', this._onSearchPartner);
        }

        get partners() {

            let pos_search_customer = this.env.pos.config.pos_search_customer;

            if ((this.state.query == "" || this.state.query === null) && pos_search_customer) {
                return []
            }else{
                return super.partners;
            }
        }

        async _onSearchPartner(event) {
            this.state.query = event.detail.searchTerm;
            const fieldName = event.detail.fieldName.toLowerCase();
            let domain = [];
            if(this.state.query != ""){
                domain = [[fieldName, "ilike", this.state.query + "%"]]
            }
            this.env.pos.db.partner_sorted = [];
            this.env.pos.db.partner_by_id = [];
            this.env.pos.db.partner_by_barcode = [];
            this.env.pos.db.partner_search_strings = [];
            if (!domain){
                this.render(true);
                return [];
            }
            const result = await this.env.services.rpc(
                {
                    model: 'pos.session',
                    method: 'get_pos_ui_res_partner_search',
                    args: [
                        [odoo.pos_session_id],
                        {
                            domain
                        },
                    ],
                    context: this.env.session.user_context,
                },
                {
                    timeout: 3000,
                    shadow: true,
                }
            );
            this.env.pos.addPartners(result);
            this.render(true);
            return result;
        }

        _getSearchFields() {
            const fields = {
                PHONE: {
                    displayName: this.env._t('Phone Number'),
                    modelField: 'phone',
                },
                NAME: {
                    displayName: this.env._t('Name'),
                    modelField: 'name',
                },
                EMAIL: {
                    displayName: this.env._t('Email'),
                    modelField: 'email',
                },
            };

            return fields;
        }

        getSearchBarConfig() {
            return {
                searchFields: new Map(
                    Object.entries(this._getSearchFields()).map(([key, val]) => [key, val.displayName])
                ),
                filter: { show: false, options: [] },
                defaultSearchDetails: {
                    fieldName: 'PARTNER_NAME',
                    searchTerm: '',
                },
                defaultFilter: null,
            };
        }

    }

    Registries.Component.extend(PartnerListScreen, SearchPartnerListScreen);

    return PartnerListScreen;
});
