odoo.define('forlife_pos_promotion.SurpriseRewardPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState, onMounted } = owl;

    class SurpriseRewardPopup extends AbstractAwaitablePopup {

        setup() {
            super.setup();
            this.state = useState({
                programRewards: this.props.programRewards
            });
            onMounted(this.selectItem);
        }

        selectItem() {
            const random_index = Math.floor(Math.random() * this.state.programRewards.length)
            let option = this.state.programRewards[random_index];
            option.isSelected = !option.isSelected;
            if (option.isSelected) {
                let others = this.state.programRewards.filter(p => p.program_id != option.program_id);
                others.forEach(option => {
                    option.isSelected = false;
                });
            };
        }

        getPayload() {
            return this.state.programRewards.find(option => option.isSelected)
        }
    }
    SurpriseRewardPopup.template = 'SurpriseRewardPopup';

    SurpriseRewardPopup.defaultProps = {
        cancelText: _lt('Cancel'),
        title: _lt('Select'),
        programRewards: [],
        confirmKey: false,
        discount_total: 0,
    };

    Registries.Component.add(SurpriseRewardPopup);
    return SurpriseRewardPopup;
});