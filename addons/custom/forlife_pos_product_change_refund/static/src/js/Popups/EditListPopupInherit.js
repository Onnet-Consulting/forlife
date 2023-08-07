odoo.define('point_of_sale.EditListPopupInherit', function(require) {
    'use strict';
    const EditListPopup = require('point_of_sale.EditListPopup');
    const Registries = require('point_of_sale.Registries');
    const { useAutoFocusToLast } = require('point_of_sale.custom_hooks');
    const { _lt } = require('@web/core/l10n/translation');
    const { useState } = owl;

    const EditListPopupInherit = (EditListPopup) =>
        class extends EditListPopup {

            setup() {
                console.log('1111111111111111111111111111111111111111');
                super.setup();
                this.state = Object.assign(this.state, useState({isBarcodeInput: this.props.isBarcodeInput}));
            }
        }

    Registries.Component.extend(EditListPopup, EditListPopupInherit);

    return EditListPopup;
});
