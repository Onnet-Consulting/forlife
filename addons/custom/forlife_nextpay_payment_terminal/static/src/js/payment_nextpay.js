odoo.define('forlife_pos_payment_terminal.payment_nextpay', function (require) {
    'use strict';

    let core = require('web.core');
    let rpc = require('web.rpc');
    let PaymentInterface = require('point_of_sale.PaymentInterface');

    let _t = core._t;

    let PaymentNextPay = PaymentInterface.extend({
        get_request_data: function (data) {
            let pos_config = this.pos.config;
            let nextpay_url = pos_config.nextpay_url;
            let nextpay_secret_key = pos_config.nextpay_secret_key;
            let nextpay_merchant_id = pos_config.nextpay_merchant_id;

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

        send_payment_request: function (cid) {
            this._super.apply(this, arguments);
            return this._nextpay_pay();
        },

        send_payment_cancel: function (order, cid) {
            this._super.apply(this, arguments);
            return this._nextpay_cancel();
        },

        close: function () {
            this._super.apply(this, arguments);
        },

        _handle_odoo_connection_failure: function (data) {
            // handle timeout
            var line = this.pos.get_order().selected_paymentline;
            if (line) {
                line.set_payment_status('retry');
            }
            this._show_error(_('Could not connect to the Odoo server, please check your internet connection and try again.'));

            return Promise.reject(data); // prevent subsequent onFullFilled's from being called
        },

        get_pos_id: function () {
            // NextPay Terminal require PoS ID has minimum 3 character
            // so we need padding here
            return this.pos.config.id.toString().padStart(3, '0');
        },

        _nextpay_pay_data: function () {
            let pos_id = this.get_pos_id();
            let order = this.pos.get_order();
            let payment_line = order.selected_paymentline;
            let customer = order.get_client() || '';
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

        _nextpay_pay: function () {
            let self = this;
            if (this.pos.get_order().selected_paymentline.amount <= 0) {
                this._show_error(_t('Cannot process transaction with negative or zero amount.'))
                return {
                    'status': 'retry'
                };
            }

            let payment_data = this._nextpay_pay_data();
            let request_data = this.get_request_data(payment_data);

            return this._call_nextpay(request_data.url, request_data.body).then(function (response) {
                return self._nextpay_handle_response(response);
            })
        },

        _nextpay_cancel: function () {
            let line = this.pos.get_order().selected_paymentline;
            if (line) {
                let cancel_payment_data = this._nextpay_cancel_data();
                let request_data = this.get_request_data(cancel_payment_data);
                return this._call_nextpay(request_data.url, request_data.body).then(function (response) {
                    return Promise.resolve();
                }).catch(function (error) {
                    return Promise.resolve();
                })
            }
            return Promise.resolve();
        },

        _call_nextpay: function (url, request_data) {
            return rpc.query({
                model: 'pos.payment.method',
                method: 'nextpay_payment_request',
                args: [url, request_data]
            }, {
                timeout: 5000,
                shadow: true
            }).catch(this._handle_odoo_connection_failure.bind(this));
        },

        _nextpay_handle_response: function (response) {
            let line = this.pos.get_order().selected_paymentline;
            if (response.resCode !== 200) {
                let msg = response.message;
                this._show_error(_.str.sprintf(_t('An unexpected error occurred. Message from NextPay: %s'), msg));
                return {
                    'status': 'retry'
                };
            } else {
                return {
                    'status': 'waitingCard'
                };
            }
        },

        _show_error: function (msg, title) {
            if (!title) {
                title = _t('NextPay Error');
            }
            this.pos.gui.show_popup('error', {
                'title': title,
                'body': msg,
            });
        },
    });

    return PaymentNextPay;
});