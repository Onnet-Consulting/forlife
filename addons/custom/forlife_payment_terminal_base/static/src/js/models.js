odoo.define('forlife_payment_terminal_base.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PaymentTerminalBase = (Payment) => class PaymentTerminalBase extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.unique_id = this.unique_id || `${this.pos.config.id}_${this.order.uid}_${(+new Date()).toString()}`;
            this.transaction_timeout = 60000; // milliseconds = 1';
            this.temp_payment_status = false; // store temporary state of payment line after send request to payment terminal
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.unique_id = json.unique_id;
            this.transaction_timeout = json.transaction_timeout;
        }

        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                unique_id: this.unique_id,
                transaction_timeout: this.transaction_timeout,
            });
        }

    }

    Registries.Model.extend(Payment, PaymentTerminalBase);


});
