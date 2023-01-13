odoo.define('forlife_pos_popup_cash.CashMoveButton2', function (require) {
    'use strict';
    const Chrome = require('point_of_sale.Chrome');
    const CashMoveButton = require('point_of_sale.CashMoveButton');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { renderToString } = require('@web/core/utils/render');

    const TRANSLATED_CASH_MOVE_TYPE = {
        in: _t('in'),
        out: _t('out'),
    };
    const CashMoveButton2 = (CashMoveButton) => class extends CashMoveButton {
        async onClick() {
            const { confirmed, payload } = await this.showPopup('CashMovePopup');
            if (!confirmed) return;
            const { type, amount, reason, reference, type_tranfer, shop} = payload;
            const translatedType = TRANSLATED_CASH_MOVE_TYPE[type];
            const formattedAmount = this.env.pos.format_currency(amount);
            if (!amount) {
                return this.showNotification(
                    _.str.sprintf(this.env._t('Cash in/out of %s is ignored.'), formattedAmount),
                    3000
                );
            }
            const extras = { formattedAmount, translatedType, reference, type_tranfer, shop };
            await this.rpc({
                model: 'pos.session',
                method: 'try_cash_in_out',
                args: [[this.env.pos.pos_session.id], type, amount, reason, extras],
            });
            if (this.env.proxy.printer) {
                const renderedReceipt = renderToString('point_of_sale.CashMoveReceipt', {
                    _receipt: this._getReceiptInfo({ ...payload, translatedType, formattedAmount }),
                });
                const printResult = await this.env.proxy.printer.print_receipt(renderedReceipt);
                if (!printResult.successful) {
                    this.showPopup('ErrorPopup', { title: printResult.message.title, body: printResult.message.body });
                }
            }
            if (type == 'in'){
                 this.showNotification(
                _.str.sprintf(this.env._t('Successfully made a cash in of %s.'), formattedAmount),
                3000
                );
            }else {
                 this.showNotification(
                _.str.sprintf(this.env._t('Successfully made a cash out of %s.'), formattedAmount),
                3000
                );
            }
            location.reload();
        }
    }
    Registries.Component.extend(CashMoveButton, CashMoveButton2);
    return CashMoveButton;
});
