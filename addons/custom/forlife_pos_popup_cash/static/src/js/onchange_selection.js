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

        confirm() {
            if (parse.float(this.state.type_tranfer) == 2 && parse.float(this.state.shop) ==0 ) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Please choose a store before confirming!');
                return;
            }
            return super.confirm();
        }


         checked_shop() {
            if($("#type").val() == 2){
                $('#shop').css('display', 'block')
                $('#shop_label').css('display', 'block')
                $('#type_store').css('margin-right', '14px');
            }
            else {
                $('#shop').css('display', 'none');
                $('#shop_label').css('display', 'none');
                $('#type_store').css('margin-right', '149px');
            }
        }

        onchangeRef(event) {
            var inputType = this.state.inputType;
            var statementLineID = parseInt($('#ref').val());
            if (statementLineID != '0') {
                var statementLine = this.env.pos.bank_statement.find((statement) => statement.id === statementLineID)
                if (statementLine && inputType == 'in') {
                    var amount = statementLine.amount;
                    var posID = statementLine.pos_config_id[0];
                    var validPos = this.env.pos.pos_customizes.find((pos_cus) => pos_cus.id == posID) || '0';
                    if (amount < 0 && posID) {
                        this.state.inputAmount = `${-amount}`;
                        this.state.type_tranfer = '2';
                        $('#type').val('2');
                        this.checked_shop();
                        this.state.shop = `${validPos.id}`;
                        $('#shop').val(`${validPos.id}`);
//                        this.state.inputReason = `Nhận tiền chuyển từ ${statementLine.pos_config_id[1]}`
                    };
                };
            } else {
                $('#type').val('0');
                $('#shop').val('0');
//                this.state.inputReason = ''
                this.checked_shop();
            };
        }

        onClickButton(type) {
            super.onClickButton(type)
            var listIdofPosTranfer = []
            var data = this.env.pos.pos_customizes
            if (type === 'in') {
                this.env.pos.bank_statement.forEach(function(item){
                    if(!listIdofPosTranfer.includes(item.pos_config_id[0])){
                        listIdofPosTranfer.push(item.pos_config_id[0])
                    }
                })
                this.env.pos.pos_customizes = this.env.pos.pos_customizes.filter(item => listIdofPosTranfer.includes(item.id))
            }else{
                this.env.pos.pos_customizes =  this.env.pos.all_pos
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
