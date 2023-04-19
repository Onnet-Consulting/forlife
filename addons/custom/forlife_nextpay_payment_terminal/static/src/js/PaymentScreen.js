odoo.define('forlife_nextpay_payment_terminal.PaymentScreen', function (require) {
    'use strict';

    const {_t} = require('web.core');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const {useBarcodeReader} = require('point_of_sale.custom_hooks');

    // Lookup table to store status and error messages
    const lookUpCodeTransaction = {
        Approved: {
            '000000': _t('Transaction approved'),
        },
        TimeoutError: {
            '001006': 'Global API Not Initialized',
            '001007': 'Timeout on Response',
            '003003': 'Socket Error sending request',
            '003004': 'Socket already open or in use',
            '003005': 'Socket Creation Failed',
            '003006': 'Socket Connection Failed',
            '003007': 'Connection Lost',
            '003008': 'TCP/IP Failed to Initialize',
            '003010': 'Time Out waiting for server response',
            '003011': 'Connect Canceled',
            '003053': 'Initialize Failed',
            '009999': 'Unknown Error',
        },
        FatalError: {
            '-1': 'Timeout error',
            '001001': 'General Failure',
            '001003': 'Invalid Command Format',
            '001004': 'Insufficient Fields',
            '001011': 'Empty Command String',
            '002000': 'Password Verified',
            '002001': 'Queue Full',
            '002002': 'Password Failed – Disconnecting',
            '002003': 'System Going Offline',
            '002004': 'Disconnecting Socket',
            '002006': 'Refused ‘Max Connections’',
            '002008': 'Duplicate Serial Number Detected',
            '002009': 'Password Failed (Client / Server)',
            '002010': 'Password failed (Challenge / Response)',
            '002011': 'Internal Server Error – Call Provider',
            '003002': 'In Process with server',
            '003009': 'Control failed to find branded serial (password lookup failed)',
            '003012': '128 bit CryptoAPI failed',
            '003014': 'Threaded Auth Started Expect Response',
            '003017': 'Failed to start Event Thread.',
            '003050': 'XML Parse Error',
            '003051': 'All Connections Failed',
            '003052': 'Server Login Failed',
            '004001': 'Global Response Length Error (Too Short)',
            '004002': 'Unable to Parse Response from Global (Indistinguishable)',
            '004003': 'Global String Error',
            '004004': 'Weak Encryption Request Not Supported',
            '004005': 'Clear Text Request Not Supported',
            '004010': 'Unrecognized Request Format',
            '004011': 'Error Occurred While Decrypting Request',
            '004017': 'Invalid Check Digit',
            '004018': 'Merchant ID Missing',
            '004019': 'TStream Type Missing',
            '004020': 'Could Not Encrypt Response- Call Provider',
            '100201': 'Invalid Transaction Type',
            '100202': 'Invalid Operator ID',
            '100203': 'Invalid Memo',
            '100204': 'Invalid Account Number',
            '100205': 'Invalid Expiration Date',
            '100206': 'Invalid Authorization Code',
            '100207': 'Invalid Authorization Code',
            '100208': 'Invalid Authorization Amount',
            '100209': 'Invalid Cash Back Amount',
            '100210': 'Invalid Gratuity Amount',
            '100211': 'Invalid Purchase Amount',
            '100212': 'Invalid Magnetic Stripe Data',
            '100213': 'Invalid PIN Block Data',
            '100214': 'Invalid Derived Key Data',
            '100215': 'Invalid State Code',
            '100216': 'Invalid Date of Birth',
            '100217': 'Invalid Check Type',
            '100218': 'Invalid Routing Number',
            '100219': 'Invalid TranCode',
            '100220': 'Invalid Merchant ID',
            '100221': 'Invalid TStream Type',
            '100222': 'Invalid Batch Number',
            '100223': 'Invalid Batch Item Count',
            '100224': 'Invalid MICR Input Type',
            '100225': 'Invalid Driver’s License',
            '100226': 'Invalid Sequence Number',
            '100227': 'Invalid Pass Data',
            '100228': 'Invalid Card Type',
        },
    };

    const PosNextpayPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            /**
             * Finish any pending input before trying to validate.
             *
             * @override
             */
            async validateOrder(isForceValidate) {
                NumberBuffer.capture();
                return super.validateOrder(...arguments);
            }

            /**
             * Finish any pending input before sending a request to a terminal.
             *
             * @override
             */
            async _sendPaymentRequest({detail: line}) {
                NumberBuffer.capture();
                return super._sendPaymentRequest(...arguments);
            }

            async _sendPaymentRequest({ detail: line }) {
                NumberBuffer.capture();
                await super._sendPaymentRequest(...arguments);
                line.set_payment_status('waitingCapture');
            }

            /**
             * @override
             */
            // deletePaymentLine(event) {
            //     const {cid} = event.detail;
            //     const line = this.paymentLines.find((line) => line.cid === cid);
            //     if (line.mercury_data) {
            //         this.do_reversal(line, false);
            //     } else {
            //         super.deletePaymentLine(event);
            //     }
            // }

        };

    Registries.Component.extend(PaymentScreen, PosNextpayPaymentScreen);

    return PaymentScreen;
});
