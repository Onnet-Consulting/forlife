odoo.define('forlife_pos_promotion.PosPromotionPartnerListScreen', function (require) {
    'use strict';

    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');

    PartnerListScreen.prototype.saveChanges = async function(event) {
        try {
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
            for (let program_id of proPrograms) {
                let validProgram = this.env.pos.promotionPrograms.find(p => p.id == program_id);
                if (promotionValidPartners.includes(program_id)) {
                    if (validProgram) {
                        validProgram.valid_customer_ids.add(partnerId);
                    };
                } else {
                    validProgram.valid_customer_ids.delete(partnerId);
                    validProgram.valid_customer_ids.delete(partnerId);
                };
            };
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
