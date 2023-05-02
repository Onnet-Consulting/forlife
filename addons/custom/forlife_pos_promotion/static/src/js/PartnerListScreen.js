odoo.define('forlife_pos_promotion.PosPromotionPartnerListScreen', function (require) {
    'use strict';

    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');
    const framework = require('web.framework');
    PartnerListScreen.prototype.saveChanges = async function(event) {
        try {
            framework.blockUI();
            let partnerId = await this.rpc({
                model: 'res.partner',
                method: 'create_from_ui',
                args: [event.detail.processedChanges],
            });
            await this.env.pos.load_new_partners();
            this.state.selectedPartner = this.env.pos.db.get_partner_by_id(partnerId);
            let proPrograms = Object.keys(this.env.pos.promotion_program_by_id);
            let promotionValidPartners = await this.rpc({
                model: 'pos.config',
                method: 'load_promotion_valid_new_partner',
                args: [[this.env.pos.config.id], [partnerId], proPrograms],
            });
            if (promotionValidPartners.length > 0) {
                for (let program_id of promotionValidPartners) {
                    let validProgram = this.env.pos.promotionPrograms.find(p => p.id == program_id);
                    if (validProgram) {
                        validProgram.valid_customer_ids.add(partnerId)
                    };
                };
            };
            framework.unblockUI();
            this.confirm();
        } catch (error) {
            if (isConnectionError(error)) {
                await this.showPopup('OfflineErrorPopup', {
                    title: this.env._t('Offline'),
                    body: this.env._t('Unable to save changes.'),
                });
            } else {
                throw error;
            }
        }
    };
});
//odoo.define('forlife_pos_promotion.PartnerListScreen', function(require) {
//    'use strict';
//
//    const Registries = require('point_of_sale.Registries');
//    const { useListener } = require("@web/core/utils/hooks");
//    const framework = require('web.framework');
//    const { isConnectionError } = require('point_of_sale.utils');
//
//    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
//
//    const PromotionPartnerListScreen = PartnerListScreen => class extends PartnerListScreen {
//
//        setup() {
//            super.setup();
//        }
//
//        async saveChanges(event) {
//            try {
//                framework.blockUI();
//                let partnerId = await this.rpc({
//                    model: 'res.partner',
//                    method: 'create_from_ui',
//                    args: [event.detail.processedChanges],
//                });
//                await this.env.pos.load_new_partners();
//                this.state.selectedPartner = this.env.pos.db.get_partner_by_id(partnerId);
//                let proPrograms = Object.keys(this.env.pos.promotion_program_by_id);
//                let promotionValidPartners = await this.rpc({
//                    model: 'pos.config',
//                    method: 'load_promotion_valid_new_partner',
//                    args: [[this.env.pos.config.id], [partnerId], proPrograms],
//                });
//                if (promotionValidPartners.length > 0) {
//                    for (let program_id of promotionValidPartners) {
//                        let validProgram = this.env.pos.promotionPrograms.find(p => p.id == program_id);
//                        if (validProgram) {
//                            validProgram.valid_customer_ids.add(partnerId)
//                        };
//                    };
//                };
//                framework.unblockUI();
//                this.confirm();
//            } catch (error) {
//                if (isConnectionError(error)) {
//                    await this.showPopup('OfflineErrorPopup', {
//                        title: this.env._t('Offline'),
//                        body: this.env._t('Unable to save changes.'),
//                    });
//                } else {
//                    throw error;
//                }
//            }
//        }
//
//    }
//
//    Registries.Component.extend(PartnerListScreen, PromotionPartnerListScreen);
//
//    return PartnerListScreen;
//});


