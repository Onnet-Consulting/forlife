/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_fast_loading.chrome", function (require) {
  "use strict";

  var models = require("point_of_sale.models");
  var rpc = require("web.rpc");
  var session = require("web.session");
  // var model_list = models.PosModel.prototype.models;
  // var product_model = null;
  // var partner_model = null;
  // var pricelist_item_model = null;
  const PosComponent = require("point_of_sale.PosComponent");
  const Registries = require("point_of_sale.Registries");
  var utils = require("web.utils");
  var round_pr = utils.round_precision;
  const { onMounted, onWillUnmount } = owl;
  const {useListener} = require("@web/core/utils/hooks");
  // for (var i = 0, len = model_list.length; i < len; i++) {
  //   if (model_list[i].model == "product.product") {
  //     product_model = model_list[i];
  //   } else if (model_list[i].model == "res.partner") {
  //     partner_model = model_list[i];
  //   } else if (model_list[i].model == "product.pricelist.item") {
  //     pricelist_item_model = model_list[i];
  //   }
  // }

  class SynchNotificationWidget extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this._onClickSessionUpdate);
        onMounted(() => this.onMounted());
    }
    onMounted() {
      var self = this;
      self.interval_id = false;
      if (!self.env.pos.config.enable_pos_longpolling) {
        if (self.env.pos.db.mongo_config.pos_live_sync == "notify")
          $(".session_update").show();
      }
      $(".session_update").click();
      var request = window.indexedDB.open("Product", 1);
      request.onupgradeneeded = function (event) {
          var db = event.target.result;
          var productsStore = db.createObjectStore('products', {
              keyPath: 'id'
          });
      };  
    }

    _onClickSessionUpdate() {
      var self = this;
      rpc
        .query({
          method: "get_products_change",
          model: "mongo.server.config",
          args: [
            {
              config_id: self.env.pos.config.id,
              product_fields: [],
              partner_model: [],
              mongo_cache_last_update_time:
                self.env.pos.db.mongo_config.cache_last_update_time,
            },
          ],
        })
        .then(function (res) {
          if (
            self.env.pos.db &&
            self.env.pos.db.mongo_config &&
            self.env.pos.db.mongo_config.pos_live_sync != "reload"
          )
            self.post_rechecking_process(res);
          self.render();
        })
        .catch(function (error, event) {
          if (event && event.preventDefault) event.preventDefault();
          $(".session_update .fa-refresh").css({
            color: "rgb(94, 185, 55)",
          });
        });
    }
    start_cache_polling() {
      var self = this;
      if (!self.interval_id)
        self.interval_id = setInterval(function () {
          if (self.env.pos.config.id) {
            setTimeout(function () {
              $.unblockUI();
            }, 3000);
            return session
              .rpc("/cache/notify", {
                company_id: self.env.pos.company.id,
                mongo_cache_last_update_time:
                  self.env.pos.db.mongo_config.cache_last_update_time,
              })
              .then(function (result) {
                if (result.sync_method == "reload") {
                  clearInterval(self.interval_id);
                  self.interval_id = false;
                } else {
                  if (result.is_data_updated) {
                    $(".session_update .fa-refresh").css({
                      color: "rgb(94, 185, 55)",
                    });
                  } else {
                    if (result.sync_method == "notify") {
                      $(".session_update .fa-refresh").css({
                        color: "#ff5656",
                      });
                      clearInterval(self.interval_id);
                      self.interval_id = false;
                    } else if (result.sync_method == "realtime") {
                      $(".session_update .fa-refresh").css({
                        color: "#ff5656",
                      });
                      if (result.data) {
                        self.post_rechecking_process(result.data);
                      }
                    }
                  }
                }
              });
          }
        }, 5000);
    }

    post_rechecking_process(res) {
      var self = this;
      if (res) {
        self.env.pos.db.mongo_config.cache_last_update_time = res.mongo_config;
        var products = res.products || false;
        var partners = res.partners || false;
        var price_deleted_record_ids = res.price_deleted_record_ids || false;
        var partner_deleted_record_ids =
          res.partner_deleted_record_ids || false;
        var product_deleted_record_ids =
          res.product_deleted_record_ids || false;
        var pricelist_items = res.pricelist_items || false;
        if (!self.env.pos.config.enable_pos_longpolling) {
          // *********************Adding and Updating the Products*******************************
          self.updatePosProducts(products, product_deleted_record_ids);
        }

        // **********************Updating Time In IndexedDB************************************
        self.updateCacheTimeIDB();


        // ***********Products deleted from indexedDB*****************************************
        self.updateProductsIDB(products, product_deleted_record_ids);

      } else {
        console.log("product not updated");
      }
    }

    update_partner_screen() {
      if ($(".load-customer-search").length) $(".load-customer-search").click();
    }
    delete_partner(partner_id) {
      var self = this;
      var partner_sorted = self.db.partner_sorted;
      var data = self.db.get_partner_by_id(partner_id);
      if (data.barcode) {
        delete self.db.partner_by_barcode[data.barcode];
      }
      // remove one element at specified index
      partner_sorted.splice(_.indexOf(partner_sorted, partner_id), 1);
      delete self.db.partner_by_id[partner_id];
      console.log(
        "############ Deleted partner (id :: %s )  ###########)",
        partner_id
      );
      self.update_partner_screen();
    }

    updatePartnerPos(partners, partner_deleted_record_ids) {
      var self = this;
      if (partners) self.env.pos.db.add_partners(partners);
      if (partner_deleted_record_ids) {
        _.each(partner_deleted_record_ids, function (partner_id) {
          self.delete_partner(partner_id);
        });
      }
    }

    updatePosProducts(products, product_deleted_record_ids) {
      var self = this;
      if (products && products.length) {
        var using_company_currency =
          self.env.pos.config.currency_id[0] ===
          self.env.pos.company.currency_id[0];
        // var conversion_rate = self.env.pos.currency.rate / self.env.pos.company_currency.rate;
        var conversion_rate = 1;
        var new_products = _.map(products, function (product) {
          if (!using_company_currency) {
            product.lst_price = round_pr(
              product.lst_price * conversion_rate,
              self.env.pos.currency.rounding
            );
          }
          product.categ = _.findWhere(self.env.pos.product_categories, {
            id: product.categ_id[0],
          });
          var new_product = new models.Product(product);
          new_product.pos = self.env.pos;
          new_product.applicablePricelistItems = {};
          for (let pricelist of self.env.pos.pricelists) {
            for (const pricelistItem of pricelist.items) {
              if (pricelistItem.product_id) {
                let product_id = pricelistItem.product_id[0];
                let correspondingProduct = productMap[product_id];
                if (correspondingProduct) {
                  if (!(pricelist.id in correspondingProduct.applicablePricelistItems)) {
                    correspondingProduct.applicablePricelistItems[pricelist.id] = [];
                  }
                  correspondingProduct.applicablePricelistItems[pricelist.id].push(pricelistItem);
                }
              }
            }
          }
          return new_product;
        });
        var stored_categories = self.env.pos.db.product_by_category_id;
        for (var i = 0, len = new_products.length; i < len; i++) {
          var product = new_products[i];
          // product.active = true;
          // product.available_in_pos = true;
          if (
            product.available_in_pos &&
            !(product.id in self.env.pos.db.product_by_id)
          ) {        
            var search_string = utils.unaccent(
              self.env.pos.db._product_search_string(product)
            );
            var categ_id = product.pos_categ_id
              ? product.pos_categ_id[0]
              : self.env.pos.db.root_category_id;
            product.product_tmpl_id = product.product_tmpl_id[0];
            if (!stored_categories[categ_id]) {
              stored_categories[categ_id] = [];
            }
            stored_categories[categ_id].push(product.id);

            if (
              self.env.pos.db.category_search_string[categ_id] === undefined
            ) {
              self.env.pos.db.category_search_string[categ_id] = "";
            }
            self.env.pos.db.category_search_string[categ_id] += search_string;

            var ancestors =
              self.env.pos.db.get_category_ancestors_ids(categ_id) || [];

            for (var j = 0, jlen = ancestors.length; j < jlen; j++) {
              var ancestor = ancestors[j];
              if (!stored_categories[ancestor]) {
                stored_categories[ancestor] = [];
              }
              stored_categories[ancestor].push(product.id);

              if (
                self.env.pos.db.category_search_string[ancestor] === undefined
              ) {
                self.env.pos.db.category_search_string[ancestor] = "";
              }
              self.env.pos.db.category_search_string[ancestor] += search_string;
            }
          }
          self.env.pos.db.product_by_id[product.id] = product;
          if (product.barcode) {
            self.env.pos.db.product_by_barcode[product.barcode] = product;
          }
        }
        //---------------------------------------------
        if (self.env.pos && self.env.pos.get_order()) {
          var order = self.env.pos.get_order();
          if (
            order.get_screen_data() &&
            order.get_screen_data().name == "ProductScreen"
          ) {
            // self.showScreen("ClientListScreen");
            self.showScreen("ProductScreen");
          }
        }
        //-----
      }
      if (product_deleted_record_ids && product_deleted_record_ids.length) {
        _.each(product_deleted_record_ids, function (record) {
          var temp = self.env.pos.db.product_by_id;
          var product = temp[record];
          var categ_search_string = self.env.pos.db._product_search_string(
            product
          );
          var new_categ_string_list = [];
          _.each(self.env.pos.db.category_search_string, function (
            categ_string
          ) {
            if (categ_string.indexOf(categ_search_string) != -1) {
              var regEx = new RegExp(categ_search_string, "g");
              var remove_string = categ_string.replace(regEx, "");
              new_categ_string_list.push(remove_string);
            } else new_categ_string_list.push(categ_string);
          });
          self.env.pos.db.category_search_string = new_categ_string_list;
          delete temp[record];
          self.env.pos.db.product_by_id = temp;
          var new_categ_list = [];
          var categories = self.env.pos.db.product_by_category_id;
          _.each(categories, function (categ) {
            var deleted_element_index = categ.indexOf(record);
            var new_list = categ.splice(deleted_element_index, 1);
            new_categ_list.push(categ);
          });
          self.env.pos.db.product_by_category_id = new_categ_list;
        });
      }
    }

    updateCacheTimeIDB() {
      var self = this;
      if (!("indexedDB" in window)) {
        console.log("This browser doesn't support IndexedDB");
      } else {
        var request = window.indexedDB.open("cacheDate", 1);
        request.onsuccess = function (event) {
          var db = event.target.result;
          if (db.objectStoreNames.contains("last_update")) {
            var transaction = db.transaction("last_update", "readwrite");
            var itemsStore = transaction.objectStore("last_update");
            var dateDataStore = itemsStore.get("time");
            dateDataStore.onsuccess = function (event) {
              var req = event.target.result;
              req = {
                id: "time",
                time: self.env.pos.db.mongo_config.cache_last_update_time,
              };
              var requestUpdate = itemsStore.put(req);
            };
          }
        };
      }
    }

    updateProductsIDB(products, product_deleted_record_ids) {
      var self = this;
      if (
        (products && products.length) ||
        (product_deleted_record_ids && product_deleted_record_ids.length)
      ) {
        if (!("indexedDB" in window)) {
          console.log("This browser doesn't support IndexedDB");
        } else {
          var request = window.indexedDB.open("Product", 1);
          request.onsuccess = function (event) {
            var db = event.target.result;
            var transaction = db.transaction("products", "readwrite");
            var itemsStore = transaction.objectStore("products");
            if (products && products.length)
              products.forEach(function (item) {
                var product = item;

                //--------------------------------------
                if (product.pos_categ_id) {
                  _.each(self.env.pos.db.category_by_id, function (categ) {
                    if (categ.id == product.pos_categ_id[0]) {
                      if (
                        self.env.pos.db.product_by_category_id[categ.id] &&
                        !self.env.pos.db.product_by_category_id[
                          categ.id
                        ].includes(product.id)
                      ) {
                        self.env.pos.db.product_by_category_id[categ.id].push(
                          product.id
                        );
                        var string = self.env.pos.db._product_search_string(
                          product
                        );
                        self.env.pos.db.category_search_string[
                          categ.id
                        ] += string;
                      }
                    }
                  });
                }
                if (
                  self.env.pos.db.product_by_category_id &&
                  !self.env.pos.db.product_by_category_id[0].includes(
                    product.id
                  )
                ) {
                  self.env.pos.db.product_by_category_id[0].push(product.id);
                  var string = self.env.pos.db._product_search_string(product);
                  self.env.pos.db.category_search_string[0] += string;
                }
                //-------------------------------------------

                var data_store = itemsStore.get(item.id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  data = item;
                  // data.active = true;
                  // data.available_in_pos = true;
                  var requestUpdate = itemsStore.put(data);
                };
              });
            if (product_deleted_record_ids && product_deleted_record_ids.length)
              product_deleted_record_ids.forEach(function (id) {
                var data_store = itemsStore.get(id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  var requestUpdate = itemsStore.delete(id);
                };
              });
          };
          request.onupgradeneeded = function (event) {
              var db = event.target.result;
              var productsStore = db.createObjectStore('products', {
                  keyPath: 'id'
              });
          };
        }
      }
    }

    updatePriceIDB(pricelist_items, price_deleted_record_ids) {
      var self = this;
      if ("indexedDB" in window) {
        if (
          (pricelist_items && pricelist_items.length) ||
          (price_deleted_record_ids && price_deleted_record_ids.length)
        ) {
          var request = window.indexedDB.open("Items", 1);
          request.onsuccess = function (event) {
            var db = event.target.result;
            var transaction = db.transaction("items", "readwrite");
            var itemsStore = transaction.objectStore("items");
            if (price_deleted_record_ids && price_deleted_record_ids.length)
              price_deleted_record_ids.forEach(function (id) {
                var data_store = itemsStore.get(id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  var requestUpdate = itemsStore.delete(id);
                };
              });
            if (pricelist_items && pricelist_items.length)
              pricelist_items.forEach(function (item) {
                var data_store = itemsStore.get(item.id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  data = item;
                  var requestUpdate = itemsStore.put(data);
                };
              });

            //---------------------------------------------
            if (self.env.pos && self.env.pos.get_order()) {
              var order = self.env.pos.get_order();
              var pricelist = order.pricelist;
              order.set_pricelist(pricelist);
              if (
                order.get_screen_data() &&
                order.get_screen_data().name == "ProductScreen"
              ) {
                // self.showScreen("ClientListScreen");
                self.showScreen("ProductScreen");
              }
            }
            //---------------------------------------------
          };
        }
      }
    }

    updatePartnerIDB(partners, partner_deleted_record_ids) {
      var self = this;
      if (
        (partners && partners.length) ||
        (partner_deleted_record_ids && partner_deleted_record_ids.length)
      ) {
        if (!("indexedDB" in window)) {
          console.log("This browser doesn't support IndexedDB");
        } else {
          var request = window.indexedDB.open("Partners", 1);
          request.onsuccess = function (event) {
            var db = event.target.result;
            var transaction = db.transaction("partners", "readwrite");
            var itemsStore = transaction.objectStore("partners");
            if (partners && partners.length)
              partners.forEach(function (item) {
                var data_store = itemsStore.get(item.id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  data = item;
                  var requestUpdate = itemsStore.put(data);
                };
              });
            if (partner_deleted_record_ids && partner_deleted_record_ids.length)
              partner_deleted_record_ids.forEach(function (id) {
                var data_store = itemsStore.get(id);
                data_store.onsuccess = function (event) {
                  var data = event.target.result;
                  var requestUpdate = itemsStore.delete(id);
                };
              });
          };
        }
      }
      //---------------------------------------------
      if (self.env.pos && self.env.pos.get_order()) {
        var order = self.env.pos.get_order();
        var pricelist = order.pricelist;
        order.set_pricelist(pricelist);
        if (
          order.get_screen_data() &&
          order.get_screen_data().name == "ProductScreen" && self
        ) {
          setTimeout(function () {
            // self.showScreen("ClientListScreen");
            self.showScreen("ProductScreen");
          }, 500);
        }
      }
      //---------------------------------------------
    }

    updatePricePos(pricelist_items, price_deleted_record_ids) {
      var self = this;
      var delete_price_data = [];
      if (
        (pricelist_items && pricelist_items.length) ||
        (price_deleted_record_ids && price_deleted_record_ids.length)
      ) {
        var pricelist_items_by_pricelist_id = {};
        _.each(pricelist_items, function (item) {
          if (item.pricelist_id[0] in pricelist_items_by_pricelist_id)
            pricelist_items_by_pricelist_id[item.pricelist_id[0]].push(item);
          else pricelist_items_by_pricelist_id[item.pricelist_id[0]] = [item];
        });
        _.each(price_deleted_record_ids, function (item) {
          delete_price_data.push(pricelist_items_by_pricelist_id);
        });
        _.each(self.env.pos.pricelists, function (pricelist) {
          var new_pricelist_items = [];
          _.each(pricelist.items, function (item) {
            if (price_deleted_record_ids.indexOf(item.id) == -1)
              new_pricelist_items.push(item);
          });
          if (pricelist_items_by_pricelist_id[pricelist.id]) {
            var pricelist_new_items = new_pricelist_items.concat(
              pricelist_items_by_pricelist_id[pricelist.id]
            );
            pricelist.items = pricelist_new_items;
          } else pricelist.items = new_pricelist_items;
          new_pricelist_items
        });
      }
    }
  }

  SynchNotificationWidget.template = "SynchNotificationWidget";

  Registries.Component.add(SynchNotificationWidget);
  return SynchNotificationWidget
});
