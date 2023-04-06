odoo.define('forlife_pos_product_change_refund.Orderline', function(require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');

    const PosChangeRefundOrderline = (Orderline) =>
        class extends Orderline {

            constructor() {
				super(...arguments);
			}

			onchangeValue(event) {
			    var self = this;
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

			async actUpdate(event) {
			    var args = {};
                args.id = this.props.line.handle_change_refund_id;
                const return_price = await this.rpc({
                    model: 'handle.change.refund',
                    method: 'get_data_update',
                    args: [args],
                })
               if (return_price) {
                    this.props.line.set_unit_price(return_price);
               }
			}

            async sendApprove(event) {
                var obj = {};
                var line = {};
                var order = this.env.pos.get_order();
                obj.pos_order_id = order.backendId;
                obj.name = order.name;
                obj.store = this.env.pos.config.store_id[0];
                line.product_id = this.props.line.product.id;
                line.price = this.props.line.price;
                line.expire_change_refund_date = this.props.line.expire_change_refund_date;
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

        };

    Registries.Component.extend(Orderline, PosChangeRefundOrderline);

    return Orderline;
});
