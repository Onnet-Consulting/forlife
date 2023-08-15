odoo.define('forlife_point_of_sale.ClosePosPopup', function (require) {
    'use strict';

    const ClosePosPopup = require('point_of_sale.ClosePosPopup');
    const Registries = require('point_of_sale.Registries');

    const ClosePosPopupInherit = (ClosePosPopup) =>
        class extends ClosePosPopup {
            async confirm() {
                if (this.hasDifference()) {
                    await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Chênh lệch tiền'),
                        body: _.str.sprintf(
                            this.env._t('Bạn không thể đóng phiên do chênh lệch tiền cuối phiên.')
                        ),
                        confirmText: this.env._t('OK'),
                    });
                } else {
                    super.confirm();
                };
            };
        };

    Registries.Component.extend(ClosePosPopup, ClosePosPopupInherit);

    return ClosePosPopup;
});
