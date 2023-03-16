odoo.define('forlife_voucher.VoucherPopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');
    const rpc = require('web.rpc');

    class VoucherPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({
                error: [],
                check_error: false,
                data: false,
                valid: true,
            });
        }

        check_voucher(codes) {
            return rpc.query({
                model: 'voucher.voucher',
                method: 'check_voucher',
                args: [codes],
                context: {
                     branch : false
                }
            });
        }



        confirm() {
            var data = this.state.data
            if(!data) return;
            var self = this;
            var check_error = this.state.check_error
            $('.o_table_error').each(function( index ) {
                  if($(this).text()){
                      check_error = true
                  }
            })
            if(this.state.valid == true && check_error == false && data != false){
                 $('.o_price_used').each(function( index ) {
                    if(data[index].value != false){
                        let price_used = $(this).val()
                        data[index].value.price_used = parseInt(price_used.split('.').join('').replace('₫',''))
                        delete data[index].value.price_change
                        delete data[index].value.price_residual
                        delete data[index].value.end_date_not_format
                    }
                 });
                 $('.o_input_priority').each(function( index ) {
                    if(data[index].value != false){
                        let priority = $(this).val()
                        data[index].value.priority = parseInt(priority)
                    }
                 });
                 for(let i=0; i< data.length; i++){
                    if(data[i].value != false){
                        this.env.posbus.trigger('close-popup', {
                            popupId: this.props.id,
                            response: {confirmed: true, payload: data},
                        });
                    }
                 }

            }else{
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(
                        this.env._t(
                            "Vui lòng kiểm tra lại thông tin Voucher"
                        ),
                    ),
                });
            }
        }

        cancel(){
            this.env.posbus.trigger('close-popup', {
                    popupId: this.props.id,
                    response: {confirmed: false, payload: false},
            });
        }

        _deleteValue(ev){
            this._onValueChange()
            var self = this;
            var data = this.state.data;
            $('.o_table_type').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).text('')
              }
            });
            $('.o_input_priority').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            $('.o_input_code').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            $('.o_table_end_date').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).text('')
              }
            });
            $('.o_table_error').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).text('')
              }
            });
            $('.o_price_residual').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            $('.o_price_used').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            var id = parseInt(ev.currentTarget.id)
            for(let i = 0; i< data.length; i++){
                if(i == id){
                    data[i].value = false;
                }
            }
            this.state.data = data
//
        }

        _onValueChange() {
            var data = this.state.data;
            var self = this;
            self.state.valid = true;
            if(data != false){
                    $('.o_price_used').each(function( index ){
                        if(data[index].value !== false && self.state.error[index].length == 0){
                            let price_used = $(this).val()
                            let price_used_convert = parseInt(price_used.split('.').join('').replace('₫',''))
                            if(price_used_convert > parseInt(data[index].value.price_residual)){
                                self.state.valid = false;
                                data[index].value.price_change = price_used_convert
                                $(this).css('color', 'red');
                            }
                            if(price_used_convert <= parseInt(data[index].value.price_residual)){
                                data[index].value.price_change = price_used_convert
                                $(this).css('color', '#444');
                            }
                        }
                })
            }
            this.state.data = data;

        }

        async check() {
            this.state.trigger = false;
            this.state.error = []
            var self = this;
            var codes = []
            $('.o_price_used').each(function( index ){
                 $(this).css('color', '#444')
            });
            $('.o_input_code').each(function( index ) {
                if($(this).val()){
                    codes.push({
                        value: $.trim($(this).val()).toUpperCase()
                    })
                }else{
                    codes.push({
                        value: false
                    })
                }

            });
            var pos_brand = false
            for(let i=0; i<this.env.pos.pos_branch.length; i++){
                pos_brand = this.env.pos.pos_branch[i].id
            }
            var data = await this.check_voucher(codes)
            $('.o_input_priority').each(function(index) {
                if(data[index].value != false){
                   $(this).val(index+1)
                }
            });
            var data_value = []
            for(let i = 0; i < data.length; i ++){
                if(codes[i].value != false && data[i].value != false){
                    data_value.push(data[i].value)
                    if(data[i].value.price_change == 0){
                        data[i].value.price_change = data[i].value.price_residual
                    }
                }
            }
            for(let i = 0; i < data.length; i ++){
                let error = [];
                if(codes[i].value != false && data[i].value == false){
                    error.push("Không tìm thấy mã voucher hợp lệ!")
                }
                if(codes[i].value != false && data[i].value != false){
                        if(data[i].value.brand_id != pos_brand){
                            error.push("Không trùng khớp mã thương hiệu!")
                        }
                        if(data[i].value.partner != false && data[i].value.partner != this.env.pos.selectedOrder.partner.id){
                            error.push("Không trùng khớp mã khách hàng!")
                        }
                        if(data[i].value.store_ids.length > 0 && data[i].value.store_ids.includes(this.env.pos.config.store_id[0]) == false){
                            error.push("Không trùng khớp mã cửa hàng!")
                        }
                        if(data[i].value.state == 'new'){
                            error.push("Mã voucher chưa được sử dụng!")
                        }
                        if(data[i].value.state == 'off value'){
                            error.push("Mã voucher đã hết giá trị sử dụng!")
                        }
                        if(data[i].value.state == 'expired'){
                            error.push("Mã voucher đã hết thời gian sử dụng!")
                        }
                        if(!data[i].value.apply_contemp_time && data_value.length > 1){
                            error.push("Voucher chỉ được sử dụng độc lập!")
                        }
                        if(this.env.pos.selectedOrder.creation_date < new Date(data[i].value.start_date)){
                            error.push("Mã voucher chưa đến thời gian sử dụng!")
                        }
                        if(this.env.pos.selectedOrder.creation_date > new Date(data[i].value.end_date_not_format)){
                            error.push("Mã voucher đã hết thời gian sử dụng!")
                        }
                }
                this.state.error.push(error)
            }
            this.state.data = data;
        }
    }

    VoucherPopup.template = "VoucherPopup";
    VoucherPopup.defaultProps = {
        title: _t("Voucher")
    };
    Registries.Component.add(VoucherPopup);

    return VoucherPopup;
})