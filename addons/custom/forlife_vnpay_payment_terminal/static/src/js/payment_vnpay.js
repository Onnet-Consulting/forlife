odoo.define('forlife_vnpay_payment_terminal.payment', function (require) {
    'use strict';

    const core = require('web.core');
    const rpc = require('web.rpc');
    const PaymentInterface = require('point_of_sale.PaymentInterface');
    const models = require('point_of_sale.models');
    const {Gui} = require('point_of_sale.Gui');

    const _t = core._t;

    let PaymentVNPay = PaymentInterface.extend({
        padding(num, size) {
            // add leading zeroes
            let s = "000000000" + num;
            return s.substring(s.length - size);
        },

        get_current_utc_datetime_values_by_datetime(datetime = new Date()) {
            // return UTC datetime values
            const pad = this.padding;
            let day = pad(datetime.getUTCDate(), 2);
            let month = pad(datetime.getUTCMonth() + 1, 2);
            let year = pad(datetime.getUTCFullYear(), 4);
            let hour = pad(datetime.getUTCHours(), 2);
            let minute = pad(datetime.getUTCMinutes(), 2);
            let second = pad(datetime.getUTCSeconds(), 2);
            let millisecond = pad(datetime.getUTCMilliseconds(), 3);
            return {
                day,
                month,
                year,
                hour,
                minute,
                second,
                millisecond
            };
        },

        get_expired_date: function () {
            let next_day = new Date();
            next_day.setDate(next_day.getDate() + 1)
            let day, month, year, hour, minute, second;
            ({day, month, year, hour, minute, second} = this.get_current_utc_datetime_values_by_datetime(next_day));
            year = year.toString().slice(-2);
            return `${year}${month}${day}${hour}${minute}`;
        },

        get_request_data: function () {
            let pos_config = this.pos.config;
            let order = this.pos.get_order();
            let payment_line = order.selected_paymentline;
            let url = pos_config.vnpay_url;
            let secret_code = pos_config.vnpay_secret_code;
            let method_code = 'VNPAY_SPOS_CARD';
            let merchant_code = pos_config.vnpay_merchant_code;
            let terminal_code = pos_config.vnpay_terminal_code;
            let merchant_method_code = pos_config.vnpay_merchant_method_code_card;
            let success_url = pos_config.vnpay_success_url || 'https://fake.url';
            let cancel_url = pos_config.vnpay_cancel_url || 'https://fake.url';
            let customer = order.get_partner();
            let user_id = (customer && customer.id || 'userId').toString();
            let order_code = order.access_token;
            let payment_amount = parseInt(payment_line.amount);
            // we will get config_id (PoS) from this client transaction code later,
            // so we can send IPN response result to correct PoS
            let client_transaction_code = payment_line.unique_id;
            let expired_date = this.get_expired_date();

            let hash_data = [
                order_code, user_id, terminal_code, merchant_code, payment_amount, success_url, cancel_url,
                client_transaction_code, merchant_method_code, method_code, payment_amount
            ]
            let hash_string = secret_code + hash_data.join('|');
            let checksum = CryptoJS.SHA256(hash_string).toString();

            let payment_value = {
                'card': {
                    'merchantMethodCode': merchant_method_code,
                    'methodCode': method_code,
                    'amount': payment_amount,
                    'clientTransactionCode': client_transaction_code
                }
            }

            let body = {
                'merchantCode': merchant_code,
                'terminalCode': terminal_code,
                'userId': user_id,
                'orderCode': order_code,
                'totalPaymentAmount': payment_amount,
                'expiredDate': expired_date,
                'payments': payment_value,
                'successUrl': success_url,
                'cancelUrl': cancel_url,
                'checksum': checksum,
            }
            return {
                url,
                body
            }
        },

        _vnpay_pay: async function () {
            let self = this;
            let line = this.pos.get_order().selected_paymentline;
            line.vnpay_received_response = false;
            line.vnpay_sent_payment = false;
            if (line.amount <= 0) {
                this._show_error(_t('Cannot process transaction with negative or zero amount.'))
                line.set_payment_status('retry');
                return false;
            }
            let request_data = this.get_request_data();

            const response = await this._call_vnpay(request_data.url, request_data.body);
            return self._vnpay_handle_response(response);
        },

        send_payment_request: async function (cid) {
            this._super.apply(this, arguments);
            await this._vnpay_pay();
            return false;
        },

        send_payment_cancel: async function (cid) {
            return await this._super.apply(this, arguments);
        },

        _call_vnpay: async function (url, request_data) {
            try {
                return await rpc.query({
                    model: 'pos.payment.method',
                    method: 'vnpay_payment_request',
                    args: [url, request_data]
                }, {
                    timeout: 10000,
                    shadow: true
                })
            } catch (error) {
                this._handle_odoo_connection_failure(error);
                return false
            }

        },

        _vnpay_handle_response: function (response) {
            let self = this;
            let line = this.pos.get_order().selected_paymentline;
            line.vnpay_received_response = true;
            line.vnpay_sent_payment = true;
            if (response.code !== '200') {
                let msg = response.message;
                this._show_error(msg);
                line.set_payment_status('retry');
            } else {
                line.set_payment_status('waitingCapture');
                clearTimeout(this.vnpay_waiting_transaction_response_timeout);
                this.vnpay_waiting_transaction_response_timeout = setTimeout(function () {
                    let line = self.pos.get_order().selected_paymentline;
                    if (line && line.vnpay_sent_payment) {
                        line.set_payment_status('timeout');
                    }
                }, self.transaction_timeout)
            }
            return true;
        },

        _handle_odoo_connection_failure: function (error) {
            let line = this.pos.get_order().selected_paymentline;
            if (line) {
                line.vnpay_received_response = false;
                line.set_payment_status('retry');
            }
            this._show_error(_.str.sprintf('Could not connect to the Odoo server.\n' +
                'Please check your internet connection and try again. \n%s'), JSON.stringify(error));
        },

        _show_error: function (msg, title) {
            if (!title) {
                title = _t('VNPay Error');
            }
            Gui.showPopup('ErrorPopup', {
                'title': title,
                'body': msg,
            });
        },
    });
    models.register_payment_method('vnpay', PaymentVNPay);

    return PaymentVNPay;
});