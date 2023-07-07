odoo.define('forlife_pos_layout.format_currency_pos', function (require) {
    'use strict';

    const CasMovePopup = require('point_of_sale.CashMovePopup');
    const Registries = require('point_of_sale.Registries');
    const {useRef, useState, onMounted, onRendered} = owl;
    const {parse} = require('web.field_utils');
    var session = require('web.session');

    const CasMovePopupFormatCurrencty = (CasMovePopup) => class extends CasMovePopup {
        setup() {
            super.setup();

            onRendered(() => {
                try {
                    const value = parse.float(this.state.inputAmount) || 0;
                    const lang = session.user_context.lang.replace('_','-')
                    const currency = this.env.pos.currency.name
                    this.state.inputAmount = value.toLocaleString(lang, {
                        currency: currency,
                    })
                } catch {}
            })
        }
    }

    Registries.Component.extend(CasMovePopup, CasMovePopupFormatCurrencty);

    return CasMovePopup;

})