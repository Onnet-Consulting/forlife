odoo.define('forlife_pos_promotion.ComboDetailsPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    class ComboDetailsPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.info = this.props.info;
        }
    }

    ComboDetailsPopup.template = 'ComboDetailsPopup';
    ComboDetailsPopup.defaultProps = {
         title: 'Combo Details',
         confirmKey: false,
         details: [],
         cancelText: _lt('Cancel')
     };
    Registries.Component.add(ComboDetailsPopup);

    return ComboDetailsPopup;
});
