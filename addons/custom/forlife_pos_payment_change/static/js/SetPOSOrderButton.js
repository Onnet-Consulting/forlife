odoo.define('forlife_pos_payment_change.SetPOSOrderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');
    const { Gui } = require('point_of_sale.Gui');

    class SetPOSOrderButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        async onClick() {
        try {
            await this.env.services.rpc({
                  model: 'sale.order',
                  method: 'browse',
                  args: [[]],
                  kwargs: { context: this.env.session.user_context },
            });
            const screen = 'POSOrderManagementScreen';
            Gui.showScreen(screen);
        } catch (e) {
            if (isConnectionError(error)) {
              this.showPopup('ErrorPopup', {
                  title: this.env._t('Network Error'),
                  body: this.env._t('Cannot access order management screen if offline.'),
              });
            } else {
              throw error;
            }
            }
        }
    };

    SetPOSOrderButton.template = 'SetPOSOrderButton';

    ProductScreen.addControlButton({
        component: SetPOSOrderButton,
        condition: function() {
            return true;
        },
    });

    Registries.Component.add(SetPOSOrderButton);

    return SetPOSOrderButton;
});