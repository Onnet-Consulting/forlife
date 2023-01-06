odoo.define('point_of_sale.CashMovePopup2', function (require) {
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
            });
            this.inputAmountRef = useRef('input-amount-ref');
        }
         checked_shop() {
            if($("#type").val() == 2){
                $('#shop').css('display', 'block')
            }
            else {
                $('#shop').css('display', 'none');
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

//    class CashMovePopup extends AbstractAwaitablePopup {
//        setup() {
//            super.setup();
//            this.state = useState({
//                inputType: '',
//                inputAmount: '',
//                inputReason: '',
//                inputHasError: false,
//                reference: '',
//                type_tranfer: '',
//                shop: ''
//            });
//            this.inputAmountRef = useRef('input-amount-ref');
//        }
//        confirm() {
//            try {
//                parse.float(this.state.inputAmount);
//            } catch (_error) {
//                this.state.inputHasError = true;
//                this.errorMessage = this.env._t('Invalid amount');
//                return;
//            }
//            if (this.state.inputType == '') {
//                this.state.inputHasError = true;
//                this.errorMessage = this.env._t('Select either Cash In or Cash Out before confirming.');
//                return;
//            }
//            if (this.state.inputType === 'out' && this.state.inputAmount > 0) {
//                this.state.inputHasError = true;
//                this.errorMessage = this.env._t('Insert a negative amount with the Cash Out option.');
//                return;
//            }
//            if (this.state.inputType === 'in' && this.state.inputAmount < 0) {
//                this.state.inputHasError = true;
//                this.errorMessage = this.env._t('Insert a positive amount with the Cash In option.');
//                return;
//            }
//            if (this.state.inputAmount < 0) {
//                this.state.inputAmount = this.state.inputAmount.substring(1);
//            }
//            return super.confirm();
//        }
//        checked_shop() {
//            if($("#type").val() == 2){
//                $('#shop').css('display', 'block')
//            }
//            else {
//                $('#shop').css('display', 'none');
//            }
//        }
//        _onAmountKeypress(event) {
//            if (event.key === '-') {
//                event.preventDefault();
//                this.state.inputAmount = this.state.inputType === 'out' ? this.state.inputAmount.substring(1) : `-${this.state.inputAmount}`;
//                this.state.inputType = this.state.inputType === 'out' ? 'in' : 'out';
//            }
//        }
//        onClickButton(type) {
//            let amount = this.state.inputAmount;
//            if (type === 'in') {
//                this.state.inputAmount = amount.charAt(0) === '-' ? amount.substring(1) : amount;
//            } else {
//                this.state.inputAmount = amount.charAt(0) === '-' ? amount : `-${amount}`;
//            }
//            this.state.inputType = type;
//            this.state.inputHasError = false;
//            this.inputAmountRef.el && this.inputAmountRef.el.focus();
//        }
//        getPayload() {
//            return {
//                amount: parse.float(this.state.inputAmount),
//                reason: this.state.inputReason.trim(),
//                type: this.state.inputType,
//                reference: this.state.reference,
//                type_tranfer:parse.float(this.state.type_tranfer),
//                shop: parse.float(this.state.shop)
//            };
//        }
//    }
//    CashMovePopup.template = 'point_of_sale.CashMovePopup';
//    CashMovePopup.defaultProps = {
//        cancelText: _t('Cancel'),
//        title: _t('Cash In/Out'),
//    };
//
//    Registries.Component.add(CashMovePopup);
//
//    return CashMovePopup;
});
