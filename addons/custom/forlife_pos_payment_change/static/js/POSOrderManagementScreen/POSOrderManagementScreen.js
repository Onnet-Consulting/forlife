odoo.define('forlife_pos_payment_change.POSOrderManagementScreen', function (require) {
    'use strict';

    const { sprintf } = require('web.utils');
    const { parse } = require('web.field_utils');
    const { useListener } = require("@web/core/utils/hooks");
    const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Registries = require('point_of_sale.Registries');
    const POSOrderFetcher = require('forlife_pos_payment_change.POSOrderFetcher');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const contexts = require('point_of_sale.PosContext');
    const { Orderline } = require('point_of_sale.models');

    const { onMounted, onWillUnmount, useState } = owl;

    class POSOrderManagementScreen extends ControlButtonsMixin(IndependentToOrderScreen) {
        setup() {
            super.setup();
            useListener('close-screen', this.close);
            useListener('click-sale-order', this._onClickPOSOrder);
            useListener('next-page', this._onNextPage);
            useListener('prev-page', this._onPrevPage);
            useListener('search', this._onSearch);

            POSOrderFetcher.setComponent(this);
            this.orderManagementContext = useState(contexts.orderManagement);

            onMounted(this.onMounted);
            onWillUnmount(this.onWillUnmount);
        }

        onMounted() {
            POSOrderFetcher.on('update', this, this.render);

            const flexContainer = this.el.querySelector('.flex-container');
            const cpEl = this.el.querySelector('.control-panel');
            const headerEl = this.el.querySelector('.header-row');
            const val = Math.trunc(
                (flexContainer.offsetHeight - cpEl.offsetHeight - headerEl.offsetHeight) /
                    headerEl.offsetHeight
            );
            POSOrderFetcher.setNPerPage(val);

            // Fetch the order after mounting so that order management screen
            // is shown while fetching.
            setTimeout(() => POSOrderFetcher.fetch(), 0);
        }

        onWillUnmount() {
            POSOrderFetcher.off('update', this);
        }

        async _getPayments(order_id) {
            let payments = await this.rpc({
                model: 'pos.payment',
                method: 'search_read',
                args: [[['pos_order_id', '=', order_id]], ['id', 'payment_method_id', 'payment_name', 'amount', 'is_voucher']],
                context: this.env.session.user_context,
            });
            let valid_methods = await this.rpc({
                model: 'pos.order',
                method: 'get_valid_methods',
                args: [order_id],
                context: this.env.session.user_context,
            });

            return {'payments': payments, 'valid_methods': valid_methods}
        }

        async _onClickPOSOrder(event) {
            const { confirmed, payload: selectedOption } = await this.showPopup('SelectionPopup',
            {
                title: this.env._t('What do you want to do?'),
                list: [{id:"0", label: this.env._t("Change Method Payment"), item: true}],
            });
            let clickedOrder = event.detail;

            let payment_values = await this._getPayments(clickedOrder.id);
            if (payment_values.payments && confirmed) {
                const {confirmed, payload} = await this.showPopup('PaymentChangePopup',
                    {
                        title: this.env._t('Payment Change: ') + clickedOrder.pos_reference,
                        payments: payment_values.payments,
                        methods: payment_values.valid_methods
                    });
                var data = Object.values(payload)
                if (data.length > 0) {
                    try {
                        await this.rpc({
                            model: 'pos.order',
                            method: 'change_payment',
                            args: [clickedOrder.id, data],
                            context: this.env.session.user_context,
                        });
                        this.showNotification(
                            _.str.sprintf(this.env._t('Successfully change the payment method on the pos order!')),
                            4000
                        );
                    }
                    catch (err) {
                        var title = this.env._t('ERROR');
                        var body = this.env._t('Fail change the payment method on the order');
                        await this.showPopup('ErrorPopup', { title, body });
                    }
                } else {
                    this.showNotification(
                        _.str.sprintf(this.env._t('Change the payment method is ignored!')),
                        4000
                    );
                }
            }
        }

        _onNextPage() {
            POSOrderFetcher.nextPage();
        }

        _onPrevPage() {
            POSOrderFetcher.prevPage();
        }

        _onSearch({ detail: domain }) {
            POSOrderFetcher.setSearchDomain(domain);
            POSOrderFetcher.setPage(1);
            POSOrderFetcher.fetch();
        }

        get orders() {
            return POSOrderFetcher.get()
        }

    }

    POSOrderManagementScreen.template = 'POSOrderManagementScreen';
    POSOrderManagementScreen.hideOrderSelector = true;

    Registries.Component.add(POSOrderManagementScreen);

    return POSOrderManagementScreen;
});