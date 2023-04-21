odoo.define('forlife_nextpay_payment_terminal.payment', function (require) {
    'use strict';

    const core = require('web.core');
    const rpc = require('web.rpc');
    const PaymentInterface = require('point_of_sale.PaymentInterface');
    const models = require('point_of_sale.models');
    const {Gui} = require('point_of_sale.Gui');

    const _t = core._t;

    // FIXME: if cashier swtich to another order , how to process the payment line of old order

    let PaymentNextPay = PaymentInterface.extend({
        send_payment_request: async function (cid) {
            await this._super.apply(this, arguments);
            await this._nextpay_pay();
            return false; // return falsy value to prevent original method set line to 'done' status
        },

        send_payment_cancel: async function (order, cid) {
            this._super.apply(this, arguments);
            return await this._nextpay_cancel();
        },

        close: function () {
            this._super.apply(this, arguments);
        },

        get_request_data: function (data) {
            let pos_config = this.pos.config;
            let nextpay_url = pos_config.nextpay_url;
            let nextpay_secret_key = pos_config.nextpay_secret_key;
            let nextpay_merchant_id = parseInt(pos_config.nextpay_merchant_id);

            data = CryptoJS.enc.Utf8.parse(JSON.stringify(data));
            nextpay_secret_key = CryptoJS.enc.Utf8.parse(nextpay_secret_key);
            let reqData = CryptoJS.AES.encrypt(data, nextpay_secret_key, {mode: CryptoJS.mode.ECB}).toString();
            return {
                'body': {
                    'reqData': reqData,
                    'merchantId': nextpay_merchant_id
                },
                'url': nextpay_url
            }
        },

        get_pos_id: function () {
            return this.pos.config.nextpay_pos_id;
        },

        _nextpay_pay_data: function () {
            let pos_id = this.get_pos_id();
            let order = this.pos.get_order();
            let payment_line = order.selected_paymentline;
            let customer = order.get_partner() || '';
            let transaction_id = payment_line.unique_id;
            return {
                "serviceName": "ADD_ORDER_INFOR",
                "orderId": transaction_id,
                "posId": pos_id,
                "amount": payment_line.amount.toString(),
                "description": customer && `${customer.name} - ${customer.phone || ''}`
            }
        },

        _nextpay_cancel_data: function () {
            let order = this.pos.get_order();
            let pos_id = this.get_pos_id();
            let payment_line = order.selected_paymentline;
            let transaction_id = payment_line.unique_id;
            return {
                "serviceName": "REMOVE_ORDER_INFOR",
                "orderId": transaction_id,
                "posId": pos_id,
                "amount": payment_line.amount.toString(),
            }
        },

        _nextpay_pay: async function () {
            let self = this;
            let line = this.pos.get_order().selected_paymentline;
            line.nextpay_received_response = false;
            line.nextpay_sent_payment = false;
            if (line.amount <= 0) {
                this._show_error(_t('Cannot process transaction with negative or zero amount.'));
                line.set_payment_status('retry');
                return false;
            }

            let payment_data = this._nextpay_pay_data();
            let request_data = this.get_request_data(payment_data);

            let response = await this._call_nextpay(request_data.url, request_data.body);
            return self._handle_nextpay_received_payment_request_response(response);
        },

        _nextpay_cancel: async function () {
            let line = this.pos.get_order().selected_paymentline;
            if (line) {
                let cancel_payment_data = this._nextpay_cancel_data();
                let request_data = this.get_request_data(cancel_payment_data);
                return await this._call_nextpay(request_data.url, request_data.body);
            }
            return false;
        },

        _call_nextpay: async function (url, request_data) {
            try {
                return await rpc.query({
                    model: 'pos.payment.method',
                    method: 'nextpay_payment_request',
                    args: [url, request_data]
                }, {
                    timeout: 10000,
                    shadow: true
                });
            } catch (error) {
                this._handle_odoo_connection_failure(error);
                return false;
            }
        },

        _handle_nextpay_received_payment_request_response: function (response) {
            let line = this.pos.get_order().selected_paymentline;
            let self = this;
            line.nextpay_received_response = true;
            line.nextpay_sent_payment = true;
            if (!response || response.resCode !== 200) {
                let msg = response.message;
                this._show_error(_.str.sprintf(_t('An unexpected error occurred. Message from NextPay: %s'), msg));
                line.set_payment_status('retry');
            } else {
                line.set_payment_status('waitingCapture');
                clearTimeout(this.nextpay_waiting_transaction_response_timeout);
                this.nextpay_waiting_transaction_response_timeout = setTimeout(function () {
                    let line = self.pos.get_order().selected_paymentline;
                    if (line && line.nextpay_sent_payment) {
                        line.set_payment_status('timeout');
                    }
                }, line.transaction_timeout)
            }
            return true;
        },

        _handle_odoo_connection_failure: function (error) {
            let line = this.pos.get_order().selected_paymentline;
            if (line) {
                line.nextpay_received_response = false;
                line.set_payment_status('retry');
            }
            this._show_error(_.str.sprintf('Could not connect to the Odoo server.\n' +
                'Please check your internet connection and try again. \n%s'), JSON.stringify(error));
        },

        _show_error: function (msg, title) {
            if (!title) {
                title = _t('NextPay Error');
            }
            Gui.showPopup('ErrorPopup', {
                'title': title,
                'body': msg,
            });
        },
    });
    models.register_payment_method('nextpay', PaymentNextPay);

    return PaymentNextPay;
});