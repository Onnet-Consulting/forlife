odoo.define('forlife_product_combo.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const ProductComboScreen = ProductScreen => class extends ProductScreen {
        async _onClickPay() {
            var order_lines = [];
            var currentOrder = this.currentOrder;
            var message = '';
            var combos = this.env.pos.product_combo;

            this.env.pos.selectedOrder.orderlines.forEach(function(item){
                order_lines.push({
                    product_id: item.product.id,
                    attribute_ids: item.product.attribute_ids,
                    product_tmpl_id: item.product.product_tmpl_id,
                    combo_id: item.product.combo_id[0],
                    product_name:item.product.display_name,
                    count: item.quantity,
                })
            })

            //nghiệp vụ đổi hàng
            if(this.env.pos.get_order().is_change_product){
                try{
                    // orders old
                    var order_old_change_lines = [];
                    var ids_old_change_lines = [];
                    var order_new_change_lines = [];
                    var ids_new_change_lines = [];

                    _.each(currentOrder.get_orderlines(), function (orderLine) {
                        var attribute_ids = orderLine.product.attribute_ids.split(",");

                       if(orderLine.product.combo_id[0] !=null && !orderLine.is_new_line && orderLine.quantity !== 0){
                            // danh sach sp cu doi tra
                            order_old_change_lines.push(orderLine);
                            ids_old_change_lines.push(orderLine.product.id);
                       }

                       if(orderLine.product.combo_id[0] !=null && orderLine.is_new_line){
                            // danh sach sp mua moi de doi tra
                            order_new_change_lines.push(orderLine);
                            ids_new_change_lines.push(orderLine.product.id);
                       }
                    })
                    var message = '';
                    if(order_old_change_lines.length != order_new_change_lines.length){
                        message = "Bạn cần mua đúng số lượng cần đổi trả!";
                    }
                    else
                    {
                        //  list combo
                        if(combos){
                            $.each(combos, $.proxy(function(i, e) {
                                var pro_combo_old_change_lines = [];
                                var pro_combo_new_change_lines = [];

                                var ids_combo_lines = [];
                                // danh sach san pham trong combo
                                _.each(e.product_combolines, function (pc) {
                                    // danh sach san pham cần doi tra
                                    _.each(order_old_change_lines, function (oldchangeLine) {
                                        if(oldchangeLine.product.product_tmpl_id == pc.product_id && e.id == oldchangeLine.product.combo_id[0]){
                                            pro_combo_old_change_lines.push(oldchangeLine);
                                        }
                                    })
                                    // danh sach san pham cần mua
                                    _.each(order_new_change_lines, function (newchangeLine) {
                                        if(newchangeLine.product.product_tmpl_id == pc.product_id && e.id == newchangeLine.product.combo_id[0]){
                                            pro_combo_new_change_lines.push(newchangeLine);
                                            ids_combo_lines.push(newchangeLine.product.id);
                                        }
                                    })
                                })

                                // kiểm tra số lượng đổi trả và mua mới xem có khớp nhau không
                                if(pro_combo_old_change_lines){
                                    _.each(pro_combo_old_change_lines, function (item_old) {
                                        if((item_old.product.attribute_ids == e.color_attribute_id || item_old.product.attribute_ids == e.size_attribute_id)){
                                            var attribute_ids = item_old.product.attribute_ids
                                        }else{
                                            if(jQuery.inArray(item_old.product.id, ids_combo_lines) == -1) {
                                                message = "Không đủ số lượng mua combo bộ vui lòng mua bổ xung";
                                            }
                                        }

                                        _.each(pro_combo_new_change_lines, function (item_new) {
                                            if(attribute_ids > 0  && attribute_ids == item_new.product.attribute_ids && item_old.product.product_tmpl_id == item_new.product.product_tmpl_id && Math.abs(item_old.quantity) != Math.abs(item_new.quantity)){
                                                message = "Bạn cần mua đúng số lượng cần đổi trả!";
                                            }else{
                                                if(item_old.product.id == item_new.product.id && Math.abs(item_old.quantity) != Math.abs(item_new.quantity)){
                                                    message = "Bạn cần mua đúng số lượng cần đổi trả!";
                                                }
                                            }
                                        })
                                    })
                                }
                            }, this));
                        }
                    }

                    if(message.length > 0) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t(
                                message
                            ),
                        });
                        return false;
                    }else{
                        return await super._onClickPay(...arguments);
                    }
                }catch(error){
                    console.log(error)
                }
            }

            // nghiệp vụ tra hang
            if(this.env.pos.get_order().is_refund_product) {
                try{
                    // danh sach don hang cu
                    var order_old_lines = [];
                    var message = '';

                    var order_refun_lines = [];

                    _.each(currentOrder.get_orderlines(), function (orderLine) {
                        // danh sach don hang cu
                       if(orderLine.product.combo_id[0] !=null && !orderLine.is_new_line ){
                            order_old_lines.push(orderLine);
                       }

                       // danh sach don hang tra lai
                       if(orderLine.product.combo_id[0] !=null && !orderLine.is_new_line &&  orderLine.quantity !=0){
                            order_refun_lines.push(orderLine);
                       }
                    })

                    //  list combo
                    $.each(combos, $.proxy(function(i, e) {
                        // so luong san pham trong combo
                        var count_pro_comboline = e.product_combolines.length;
                        var count_order_refun_line = 0;

                        // danh sach san pham trong combo
                        _.each(e.product_combolines, function (pc) {

                            // danh sach sp tra lai
                            var product_check_combo = [];
                            _.each(order_refun_lines, function (refunLine) {
                                if(refunLine.product.product_tmpl_id == pc.product_id){
                                    count_order_refun_line = count_order_refun_line + 1;
                                    // neu so luong san pham tra lai nho hon so luong toi thieu trong combo
                                    if(Math.abs(refunLine.quantity) < pc.quantity){
                                        message = "Bạn cần trả đúng số lượng combo sản phẩm đã mua!";
                                    }

                                    if (Math.abs(refunLine.quantity) % pc.quantity != 0) {
                                        message = "Bạn cần trả đúng số lượng combo sản phẩm đã mua!";
                                    }

                                    var value = Math.abs(refunLine.quantity) / pc.quantity;
                                    if (jQuery.inArray(value, product_check_combo) == -1) {
                                        product_check_combo.push(value);
                                    }
                                    if (product_check_combo.length > 1) {
                                        message = "Không đủ số lượng mua combo bộ vui lòng mua bổ xung";
                                    }
                                }
                            })
                        })

                         //  Nếu mua khong du cac san pham co trong cung 1 combo
                        if(count_pro_comboline != count_order_refun_line){
                            message = "Bạn cần trả đủ các sản phẩm đã mua trong combo!";
                        }
                    }, this));

                    if(message.length > 0) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t(
                                message
                            ),
                        });
                        return false;
                    }else{
                        return await super._onClickPay(...arguments);
                    }
                }catch(error){
                    console.log(error)
                }
            }

            // nghiep vu  mua combo
            if (!currentOrder.is_change_product && !currentOrder.is_refund_product) {
                // check product combo
                try{
                    var list_product_checked = [];
                    if(combos) {
                        var message = '';
                        order_lines.forEach(function(item){
                            // kiem tra xem id có trong mang khong neu k co thi them vao
                            if(jQuery.inArray(item.product_id, list_product_checked) == -1) {
                                list_product_checked.push(item.product_id);
                                var product_check_combo = [];
                                $.each(combos, $.proxy(function(i, e) {
                                    if(e.id == item.combo_id) {
                                        e.product_combolines.forEach(function (pc) {
                                            var line2 = [];
                                            order_lines.forEach(function(pp) {
                                                if(pp.product_tmpl_id == pc.product_id){
                                                    line2.push(pp);
                                                }
                                            })
                                            var total_quantity = 0
                                            line2.forEach(function (li) {
                                                if (jQuery.inArray(li.product_id, list_product_checked) == -1) {
                                                    list_product_checked.push(li.product_id);
                                                }
                                                total_quantity = total_quantity + li.count
                                            })
                                            //  kiem tra tong so luong cua san pham trong 1 combo
                                            if (total_quantity < pc.quantity) {
                                                message = "Mã " + pc.sku_code + " thuộc bộ nên cần phải hoàn thành bộ khi mua";
                                            }

                                            if (total_quantity % pc.quantity != 0) {
                                                message = "Mã " + pc.sku_code + " thuộc bộ nên cần phải hoàn thành bộ khi mua";
                                            }

                                            var value = total_quantity / pc.quantity;
                                            if (jQuery.inArray(value, product_check_combo) == -1) {
                                                product_check_combo.push(value);
                                            }
                                            if (product_check_combo.length > 1) {
                                                message = "Không đủ số lượng mua combo bộ vui lòng mua bổ xung";
                                            }
                                        });
                                    }
                                }, this));
                            }
                        })

                        if(message.length > 0) {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Warning'),
                                body: this.env._t(
                                    message
                                ),
                            });
                            return false;
                        }
                        else{
                            return await super._onClickPay(...arguments);
                        }
                    }
                }catch(error){
                    console.log(error)
                }
            }
        }
    };

    Registries.Component.extend(ProductScreen, ProductComboScreen);

    return ProductScreen;

});
