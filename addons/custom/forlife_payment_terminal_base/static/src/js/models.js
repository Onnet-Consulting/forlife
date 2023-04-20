odoo.define('forlife_payment_terminal_base.models', function (require) {
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const PaymentTerminalBase = (Payment) => class PaymentTerminalBase extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.unique_id = this.unique_id || `${this.pos.config.id}_${(+new Date()).toString()}`;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.unique_id = json.unique_id;
        }

        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                unique_id: this.unique_id,
            });
        }
    }

    Registries.Model.extend(Payment, PaymentTerminalBase);


});
