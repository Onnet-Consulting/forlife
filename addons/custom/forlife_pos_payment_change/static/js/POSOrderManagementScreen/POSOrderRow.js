odoo.define('forlife_pos_payment_change.POSOrderRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const utils = require('web.utils');

    /**
     * @props {models.Order} order
     * @props columns
     * @emits click-order
     */
    class POSOrderRow extends PosComponent {
        get order() {
            return this.props.order;
        }
        get highlighted() {
            const highlightedOrder = this.props.highlightedOrder;
            return !highlightedOrder ? false : highlightedOrder.backendId === this.props.order.backendId;
        }

        // Column getters //

        get name() {
            return this.order.pos_reference;
        }
        get date() {
            return moment(this.order.date_order).format('YYYY-MM-DD hh:mm A');
        }
        get partner() {
            const partner = this.order.partner_id;
            return partner ? partner[1] : null;
        }
        get total() {
            return this.env.pos.format_currency(this.order.amount_total);
        }
        /**
         * Returns true if the order has unpaid amount, but the unpaid amount
         * should not be the same as the total amount.
         * @returns {boolean}
         */
        get showAmountUnpaid() {
            const isFullAmountUnpaid = utils.float_is_zero(Math.abs(this.order.amount_total - this.order.amount_unpaid), this.env.pos.currency.decimal_places);
            return !isFullAmountUnpaid && !utils.float_is_zero(this.order.amount_unpaid, this.env.pos.currency.decimal_places);
        }
        get amountUnpaidRepr() {
            return this.env.pos.format_currency(this.order.amount_unpaid);
        }
        get state() {
            let state_mapping = {
              'draft': this.env._t('New'),
              'cancel': this.env._t('Cancel'),
              'paid': this.env._t('Paid'),
              'done': this.env._t('Posted'),
              'invoiced': this.env._t('Invoiced'),
            };

            return state_mapping[this.order.state];
        }
        get salesman() {
            const salesman = this.order.employee_id;
            return salesman ? salesman[1] : null;
        }
    }
    POSOrderRow.template = 'POSOrderRow';

    Registries.Component.add(POSOrderRow);

    return POSOrderRow;
});
