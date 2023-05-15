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
                expense_label: '',
                inputAmount: '',
                inputType: '',
                inputReason: '',
                inputHasError: false,
                old_pos: this.props.old_pos
            });
            this.inputAmountRef = useRef('input-amount-ref');
        }

        confirm() {
            if (parse.float(this.state.type_tranfer) == 2 && parse.float(this.state.shop) ==0 ) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Please choose a store before confirming!');
                return;
            }
            if (parse.float(this.state.type_tranfer) == 4 && (parse.float(this.state.expense_label) == 0 || this.state.inputType == 'in')) {
                this.state.inputHasError = true;
                this.errorMessage = this.env._t('Please choose a expense label before confirming!');
                return;
            }
            return super.confirm();
        }


         checked_shop() {
            if($("#type").val() == 2){
                $('#shop').css('display', 'block')
                $('#shop_label').css('display', 'block')
                $('#type_store').css('margin-right', '14px');
                // hide expense_label
                $('#expense_label').css('display', 'none')
                $('#expense_label_label').css('display', 'none')
            }
            else if ($("#type").val() == 4 && this.state.inputType == 'out') {
                $('#expense_label').css('display', 'block')
                $('#expense_label_label').css('display', 'block')
                $('#shop').css('display', 'none');
                $('#shop_label').css('display', 'none');
            }
            else {
                $('#shop').css('display', 'none');
                $('#shop_label').css('display', 'none');
                $('#type_store').css('margin-right', '149px');
                // hide expense_label
                $('#expense_label').css('display', 'none')
                $('#expense_label_label').css('display', 'none')
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
                this.checked_shop();
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
            if (type === 'in') {
                this.env.pos.bank_statement.forEach(function(item){
                    if(!listIdofPosTranfer.includes(item.pos_config_id[0])){
                        listIdofPosTranfer.push(item.pos_config_id[0])
                    }
                })
                this.env.pos.pos_customizes = this.env.pos.pos_customizes.filter(item => listIdofPosTranfer.includes(item.id))
                this.checked_shop()
            }else{
                this.env.pos.pos_customizes =  this.state.old_pos
                this.checked_shop()
            }

        }

        getPayload() {
            var res = super.getPayload()
            res.reference = this.state.reference,
            res.type_tranfer = parse.float(this.state.type_tranfer),
            res.shop= parse.float(this.state.shop)
            res.expense_label = parse.float(this.state.expense_label)
            return res
        }
    };
    Registries.Component.extend(CashMovePopup, CashMovePopup2);
    return CashMovePopup;

});
