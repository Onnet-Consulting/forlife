odoo.define('forlife_voucher.PosPaymentScreenVoucher', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    const PosPaymentScreenVoucher = (PaymentScreen) =>
        class extends PaymentScreen {
            setup() {
                super.setup();
            }

            async addNewPaymentLine({ detail: paymentMethod }) {
                if(!this.env.pos.data_voucher){
                    this.env.pos.data_voucher = false
                }
                if(!this.env.pos.count_popups){
                    this.env.pos.count_popups = 0
                }
                var data_voucher = this.env.pos.data_voucher;
//                if(this.env.pos.count_popups>1){
//
//                }
                this.env.pos.count_popups = this.env.pos.count_popups + 1;
                if(paymentMethod.is_voucher){
                    const {confirmed, payload: data} = await this.showPopup('VoucherPopup', {
                        confirm: this.env._t('Xác nhận'),
                        title: this.env._t('Voucher'),
                        cancel: this.env._t('Hủy')
                    });
                    if(!confirmed){
                        return;
                    }
                    let result = this.currentOrder.add_paymentline(paymentMethod);
                    var price_used = 0;
                    if(confirmed){
                        if(data){
                            for(let i=0; i< data.length; i++){
                                if (data[i].value){
                                    price_used += data[i].value.price_used
                                    data[i].value.payment_method_id = paymentMethod.id
                                }
                            }
                            this.currentOrder.addVoucherline(data);
                            result.amount = price_used;
                        }
                    }
                    if (result){
                        NumberBuffer.reset();
                        return true;
                    }
                    else{
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Error'),
                            body: this.env._t('There is already an electronic payment in progress.'),
                        });
                        return false;
                    }

                }else{
                    let result = this.currentOrder.add_paymentline(paymentMethod);
                    if (result){
                        NumberBuffer.reset();
                        return true;
                    }
                    else{
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Error'),
                            body: this.env._t('There is already an electronic payment in progress.'),
                        });
                        return false;
                    }
                }
            }
        };

    Registries.Component.extend(PaymentScreen, PosPaymentScreenVoucher);

    return PosPaymentScreenVoucher;
});
