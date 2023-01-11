odoo.define('forlife_pos_change_payment_method.SetPaidPosOrdersButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');
    const { Gui } = require('point_of_sale.Gui');

    class SetPaidPosOrdersButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        async onClick() {
          try {
              await this.env.services.rpc({
                  model: 'pos.order',
                  method: 'browse',
                  args: [[]],
                  kwargs: { context: this.env.session.user_context },
              });
              const screen = this.env.isMobile ? 'MobileSaleOrderManagementScreen' : 'SaleOrderManagementScreen';
              Gui.showScreen(screen);
          } catch (error) {
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
    }
    SetPaidPosOrdersButton.template = 'SetPaidPosOrdersButton';

    ProductScreen.addControlButton({
        component: SetPaidPosOrdersButton,
        condition: function() {
            return true;
        },
    });

    Registries.Component.add(SetPaidPosOrdersButton);

    return SetPaidPosOrdersButton;
});
