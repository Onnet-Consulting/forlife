odoo.define('forlife_pos_popup_cash.CashMovePopup', function (require) {
    'use strict';
    const Chrome = require('point_of_sale.Chrome');
    const CashMovePopup = require('point_of_sale.CashMovePopup');
    const Registries = require('point_of_sale.Registries');
    const {_t} = require('web.core');
    const {renderToString} = require('@web/core/utils/render');

    const CashMovePopupCustom = (CashMovePopup) => class extends CashMovePopup {
        confirm() {
            let origin_input_amount = this.state.inputAmount;
            let input_type = this.state.inputType;
            if (input_type === 'out' && origin_input_amount && origin_input_amount.charAt(0) !== '-') {
                this.state.inputAmount = '-' + this.state.inputAmount;
            }
            super.confirm();
        }

        onClickButton(type) {
            super.onClickButton(...arguments)
            let origin_input_amount = this.state.inputAmount;
            if (origin_input_amount) {
                this.state.inputAmount = origin_input_amount.replace('-', '');
            }
            this.inputAmountRef.el && this.inputAmountRef.el.focus();
        }

    }

    Registries.Component.extend(CashMovePopup, CashMovePopupCustom);
    return CashMovePopupCustom;
})
