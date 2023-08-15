odoo.define('forlife_pos_product_change_refund.OrderlineChangeRefund', function(require) {
    'use strict';

    const OrderlineChangeRefund = require('forlife_pos_layout.OrderlineChangeRefund');
    const Registries = require('point_of_sale.Registries');

    const OrderlineChangeRefundExtend = (OrderlineChangeRefund) =>
        class extends OrderlineChangeRefund {

            constructor() {
				super(...arguments);
			}

			onchangeValue(event) {
			    var self = this;
			    var order_new = this.env.pos.get_order()
			    var old_id_employee;
			    if(order_new.hasOwnProperty('old_id_employee')){
			        old_id_employee = order_new.old_id_employee
			    }else{
			        old_id_employee = false
			    }
			    if(event.target.value > 0 &&  order_new.is_change_product){
			        let user = this.env.pos.user;
                    if (user.employee_id) {
                        self.props.line.employee_id = user.employee_id[0];
                    }
			    }else {
			        if(old_id_employee){
			            old_id_employee.forEach(function(item){
			                if(item.id == self.props.line.id){
			                    self.props.line.employee_id = item.employee_id
			                }
			            })
			        }
			    }
			    if (event.target.value > self.props.line.quantity_canbe_refund) {
			        self.showPopup('ErrorPopup', {
                        title: self.env._t('Warning'),
                        body: self.env._t("You can't change or refund quantity bigger quantity available."),
                    });
                    return false
			    }
			    var today = new Date();
                today.setHours(0, 0, 0, 0);

			    var orderlines = this.env.pos.get_order().get_orderlines();
			    self.props.line.set_quantity(- parseInt(event.target.value) || 0);
			    // compare with order line of Order
			    orderlines.forEach(function(orderline) {
			        if (orderline.quantity !== 0 && orderline.id !== self.props.line.id && event.target.value !== '') {
			            var current_date = new Date(self.props.line.expire_change_refund_date);
			            current_date.setHours(0, 0, 0, 0);

			            var compare_date = new Date(orderline.expire_change_refund_date);
			            compare_date.setHours(0, 0, 0, 0);

			            if ((current_date < today && compare_date > today) || (current_date > today && compare_date < today)) {
			                self.props.line.set_quantity(0);
			                self.showPopup('ErrorPopup', {
                                title: self.env._t('Warning'),
                                body: self.env._t("You can't change or refund product expiry date and out of date in single order. " +
                                "Please split order for products expiry date and products out of date."),
                            });
                            return false
			            }
			        }
                })
//                var setArr = [].slice.call($('input.input-change-refund.change'));
//                for( var i in setArr )
//                   if( setArr[i] !== event.target && setArr[i].value !== '')
//                     console.log(i);

			}

			onchangeValueNew(event) {
			    var self = this;
			    self.props.line.set_quantity(parseInt(event.target.value) || 0, true);
			}

			isShowChangeProduct() {
			    let line = this.props.line;
			    if (line.order.is_change_product && line.quantity && !line.get_alternative_lines().length && line.refunded_orderline_id) return true;
			    return false;
			}

			async actUpdate(event) {
			    var args = {};
                args.id = this.props.line.handle_change_refund_id;
                var data_update = await this.rpc({
                    model: 'handle.change.refund',
                    method: 'get_data_update',
                    args: [args],
                })
                if (data_update.status === 'approve') {
                    this.props.line.handle_change_refund_price = data_update.price;
                    this.props.line.beStatus = true;
                    const order = this.env.pos.get_order();
                    if (order) {
                        order.approved = true;
                    }
                }else {
                    this.props.line.beStatus = false;
                }
			}

            async sendApprove(event) {
                if (this.props.line.reason_refund_id === 0 || this.props.line.get_quantity() === 0) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Warning'),
                        body: this.env._t("Please select reason refund and set quantity!")
                    });
                    return;
                }

                var obj = {};
                var line = {};
                var order = this.env.pos.get_order();
                obj.pos_order_id = order.origin_pos_order_id;
                obj.store = this.env.pos.config.store_id[0];
                obj.is_change_product = order.is_change_product;
                obj.is_refund_product = order.is_refund_product;
                line.product_id = this.props.line.product.id;
                var price = this.props.line.price;
                if (this.props.line.quantity_canbe_refund > 0) {
                    price -= (this.props.line.money_is_reduced / this.props.line.quantity_canbe_refund);
                }
                line.price = price;
                line.expire_change_refund_date = this.props.line.expire_change_refund_date;
                line.refunded_orderline_id = this.props.line.refunded_orderline_id;
                line.reason_refund_id = this.props.line.reason_refund_id;
                obj.lines = [line];

                this.props.line.approvalStatus = true;
                try {
                    const id = await this.rpc({
                        model: 'handle.change.refund',
                        method: 'create_from_ui',
                        args: [obj]
                    });
                    if (id) {
                        this.props.line.handle_change_refund_id = id;
                    }
                }
                catch (err) {
                    var title = this.env._t('ERROR');
                    var body = this.env._t("You can't create record handle Change Refund!");
                    await this.showPopup('ErrorPopup', { title, body });
                }

            }

            async actChangeProduct(event) {
                console.log(this.env.pos);
                let orderline = this.props.line;
                let order = this.env.pos.get_order();
                let pos = this.env.pos;
                console.log('event.detail', event);
                const { confirmed, payload } = await this.showPopup('EditListPopup', {
                    title: this.env._t('Choose New Alternative Product'),
                    isSingleItem: false,
                    array: [],
                    isBarcodeInput: true
                });
                if (confirmed) {
                    const newBarcodeLines = payload.newArray
                        .map(item => ({ product_barcode: item.text }));
                    let toAddProducts = []
                    newBarcodeLines.forEach(bar => {
                        let product = this.env.pos.db.product_by_barcode[bar.product_barcode];
                        if (product) {
                            toAddProducts.push(product);
                        };
                    });
                    if (!toAddProducts.length) {
                        return;
                    };
                    const promotion_data = await this.rpc({
                        model: 'pos.config',
                        method: 'check_promotion_for_change_products',
                        args: [[pos.config.id], [orderline.refunded_orderline_id], toAddProducts.map(p=>p.id)]
                    });
                    if (promotion_data) {
                        let {program_data, pricelist_data} = promotion_data;
                        if (program_data.length && pricelist_data.length) {
                            program_data = program_data.filter(p => !pos.promotion_program_by_id.hasOwnProperty(p.id));
                            pricelist_data = pricelist_data.filter(pl => !pos.pro_pricelist_item_by_id.hasOwnProperty(pl.id));
                            pos.promotionPrograms.push(...program_data);
                            pos._loadPromotionData(program_data);
                            pos._loadPromotionPriceListItem(pricelist_data);
                            order.finished_programs.push(...program_data.map(p=>p.id))
                        }
                    };
                    for (let product of toAddProducts) {
                        let options = {
                            related_refund_line_cid: orderline.cid
                        };
                        order.add_product(product, options);
                    };
                }
            }

            getTotalDiscount() {
                // TODO: class được extend từ class forlife_pos_layout.OrderlineChangeRefund
                // TODO: => kết quả super.getTotalDiscount(...args) == 0.0.
                // TODO: Do đó, phải thực hiện như cách ở dưới
//                var total = super.getTotalDiscount(...arguments);
                var total = 0.0;
                if(this.props.line.money_reduce_from_product_defective > 0) {
                    total += this.props.line.money_reduce_from_product_defective;
                };
                // Card rank
                total += this.props.line.get_card_rank_discount();
                // Promotion Program
                const applied_promotions = this.props.line.get_applied_promotion_str();
                for (const applied_promotion of applied_promotions) {
                    if (applied_promotion) {
                        total += applied_promotion.discount_amount;
                    };
                };
                // Point Order
                if (this.props.line.point) {
                    total += Math.abs(this.props.line.point);
                };
                //
                return total;
            }

            getPercentDiscountRefund() {
                var percent_discount = 0;
                var percent_handle_change_refund_price = 0;
                var reduced = Math.abs(this.props.line.money_is_reduced);
                var quantity = this.props.line.get_quantity();
                var order_amount = this.props.line.get_unit_display_price() * quantity;
                var quantity_can_refund = this.props.line.quantity_canbe_refund;
                if (order_amount !== 0 && quantity_can_refund !== 0) {
                    if(quantity!=0){
                       percent_discount = ((reduced * quantity / quantity_can_refund) / order_amount) * 100;
                    }else{
                       percent_discount=0;
                    }
                }
                if(order_amount != 0){
                    percent_handle_change_refund_price = Math.abs(this.props.line.handle_change_refund_price/order_amount)*100
                }else{
                    percent_handle_change_refund_price = 0
                }
                percent_discount = percent_discount + percent_handle_change_refund_price
                return Math.round(percent_discount * 100) / 100;
            }

        };

    Registries.Component.extend(OrderlineChangeRefund, OrderlineChangeRefundExtend);

    return OrderlineChangeRefund;
});
