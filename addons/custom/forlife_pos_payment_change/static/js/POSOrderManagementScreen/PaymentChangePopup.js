odoo.define('forlife_pos_payment_change.PaymentChangePopup', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');
    const { debounce } = require("@web/core/utils/timing");
    const { useListener } = require("@web/core/utils/hooks");
    const { useAutoFocusToLast } = require('point_of_sale.custom_hooks');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState } = owl;

    class PaymentChangePopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({payload: [] })
        }

        selectLine() {
            var line_nodes = $('.payment-item')
            var payload = []
            line_nodes.each((index, el) => {
                var payment_id = $(el).find('.o_payment_id').attr("value")
                var amount = $(el).find('.o_payment_amount').attr("value")
                var payment_method_id = $(el).find('.o_payment_method_id').find(':selected').attr("value")
                if (payment_id && payment_method_id) {
                    this.state.payload.push({
                        'payment_id': parseInt(payment_id),
                        'amount': parseInt(amount),
                        'payment_method_id': parseInt(payment_method_id)
                    })
                }
            })
        }
        getPayload() {
        console.log('---------------' + this.state.payload)
        console.dir(this.state.payload)
            return this.state.payload
        }

    }

    PaymentChangePopup.template = 'PaymentChangePopup';

    PaymentChangePopup.defaultProps = {
        cancelText: _lt('Cancel'),
        title: _lt('Change Payment'),
        payload: [],
        payments: [],
        methods: [],
        confirmKey: false,
    };

    Registries.Component.add(PaymentChangePopup);

    return PaymentChangePopup;

});
