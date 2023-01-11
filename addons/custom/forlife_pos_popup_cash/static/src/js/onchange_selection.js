odoo.define('forlife_pos_popup_cash.CashMovePopup2', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const CashMovePopup = require('point_of_sale.CashMovePopup');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    const { useRef, useState } = owl;
    const CashMovePopup2 = (CashMovePopup) => class extends CashMovePopup {
        setup() {
            super.setup();
            this.state = useState({
                reference: '',
                type_tranfer: '',
                shop: '',
                inputAmount: '',
                inputType: '',
                inputReason: '',
                inputHasError: false,
            });
            this.inputAmountRef = useRef('input-amount-ref');
        }
         checked_shop() {
            if($("#type").val() == 2){
                $('#shop').css('display', 'block')
                $('#shop_label').css('display', 'block')
                $('#type_store').css('margin-right', '0px');
                $('#type_store').css('margin-left', '19px');
            }
            else {
                $('#shop').css('display', 'none');
                $('#shop_label').css('display', 'none');
                $('#type_store').css('margin-right', '50px');
                $('#type_store').css('margin-left', '0px');
            }
        }
        getPayload() {
            var res = super.getPayload()
            res.reference = this.state.reference,
            res.type_tranfer = parse.float(this.state.type_tranfer),
            res.shop= parse.float(this.state.shop)
            return res
        }
    };
    Registries.Component.extend(CashMovePopup, CashMovePopup2);
    return CashMovePopup;

});
