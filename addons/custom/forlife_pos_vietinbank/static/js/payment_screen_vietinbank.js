odoo.define('forlife_pos_vietinbank.payment_screen_vietinbank', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener, useOwnedDialogs, useService} = require("@web/core/utils/hooks");
    const {SelectCreateDialog} = require("@web/views/view_dialogs/select_create_dialog");
    const rpc = require('web.rpc');

    const PosVietinBank = (PaymentScreen) => class extends PaymentScreen {
        setup() {
            super.setup();
            useListener('get-transaction-vietinbank', this._getTransactionFromVietinBank);
            this.addDialog = useOwnedDialogs();
        }

        async _getTransactionFromVietinBank({detail: line}) {
            const dataLine = line
            const self = this
            await rpc.query({
                model: 'apis.vietinbank',
                method: 'get_list_transaction_info',
                args: [[line.pos.config.id, line.payment_method.id, line.order.pos_session_id]],
            }).then(async function (res) {
                if (res[0]) {
                    self.addDialog(SelectCreateDialog, {
                        title: 'Vấn tin sao kê',
                        noCreate: true,
                        multiSelect: true,
                        resModel: 'vietinbank.transaction.model',
                        context: {},
                        domain: [
                            ['pos_order_id', '=', line.pos.config.id],
                            ['payment_method_id', '=', line.payment_method.id],
                            ['session_id', '=', dataLine.order.pos_session_id]
                        ],
                        onSelected: async (resIds) => {
                            await rpc.query({
                                model: 'apis.vietinbank',
                                method: 'total_amount',
                                args: [resIds],
                            }).then(async function (res) {
                                dataLine.set_amount(res)
                                dataLine.set_payment_status('done')
                            })
                        }
                    });
                } else {
                    alert(res[1])
                }
            })

        }

        deletePaymentLine(event) {
            super.deletePaymentLine(event);
            $(this.el).find('.numpad button').css('pointer-events', 'auto')
        }

        addNewPaymentLine({detail: paymentMethod}) {
            super.addNewPaymentLine({detail: paymentMethod});
            if (paymentMethod.use_payment_terminal === 'vietinbank') {
                $(this.el).find('.numpad button').css('pointer-events', 'none')
            }
        }
    }

    Registries.Component.extend(PaymentScreen, PosVietinBank);
    return PaymentScreen;
})