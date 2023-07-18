import random
import string
from datetime import date, datetime, timedelta

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    # return result_str + datetime.strptime("%Y%d%m%H%M%S%f")
    return result_str


def create_move_line(self, line, lines_store={}, product_line_rel={}):
    if line.product_id:
        product_id = line.product_id.id
        row = {line.id: line}

        if product_line_rel.get(product_id):
            old_row = product_line_rel[product_id]
            add_line = True
            for k, v in old_row.items():
                if v.price_bkav == line.price_bkav:
                    add_line = False
                    lines_store[k]["quantity"] += v.qty
                    invoice_ids = lines_store[k]["invoice_ids"]
                    invoice_ids.append(line.order_id.id)
                    lines_store[k]["invoice_ids"] = list(set(invoice_ids))
                    break
            if add_line:
                product_line_rel[product_id].update(row)
                lines_store[line.id] = {
                    "product_id": product_id,
                    "quantity": line.qty,
                    "price_unit": line.price_bkav,
                    "invoice_ids": [line.order_id.id]
                }
        else:
            product_line_rel[product_id] = row
            lines_store[line.id] = {
                "product_id": product_id,
                "quantity": line.qty,
                "price_unit": line.price_bkav,
                "invoice_ids": [line.order_id.id]
            }

        
def compare_move_lines(
    self, 
    items={}, 
    store={}, 
    lines=[], 
    missing_line=[], 
    page=0, 
    first_n=0, 
    last_n=1000
):
    pk = f"{store.id}_{page}"
    lines_store = {}
    product_line_rel = {}
    if len(lines) > last_n:
        n = last_n - 1
        if x:= len(missing_line):
            n = n - x
        
        for line in missing_line:
            create_move_line(self, line, lines_store, product_line_rel)

        missing_line = []

        last_line = lines[n]
        pre_last_line = lines[n - 1]

        po_order_id = None
        if pre_last_line.order_id == last_line.order_id:
            po_order_id = last_line.order_id.id

        separate_lines = lines[first_n:last_n]
        del lines[first_n:last_n]

        for line in separate_lines:
            if po_order_id and line.order_id.id == po_order_id:
                missing_line.append(line)
                continue

            create_move_line(self, line, lines_store, product_line_rel)

        
        items[pk] = {
            'code': get_random_string(32),
            'company_id': self.env.company.id,
            'store_id': store.id,
            'partner_id': store.contact_id.id,
            'invoice_date': date.today(),
            'line_ids': list(lines_store.values())
        }
        page += 1
        compare_move_lines(
            self, 
            items=items, 
            store=store, 
            lines=lines, 
            missing_line=missing_line, 
            page=page, 
            first_n=first_n, 
            last_n=last_n
        )
    else:
        for line in lines:
            create_move_line(
                self,
                line, 
                lines_store, 
                product_line_rel
            )
        items[pk] = {
            'code': get_random_string(32),
            'company_id': self.env.company.id,
            'store_id': store.id,
            'partner_id': store.contact_id.id,
            'invoice_date': date.today(),
            'line_ids': list(lines_store.values())
        }


def collect_invoice_to_bkav_end_day(self, move_type, model, model_line):
    invoice_model = self.env['account.move']
    today = date.today() - timedelta(days=1)
    domain = [
        ('company_id', '=', self.env.company.id),
        ('is_post_bkav', '=', False),
        ('move_type', '=', move_type),
        ('invoice_date', '<=', today),
        ('pos_order_id', '!=', False), 
    ]
    sale_invoices = invoice_model.search(domain)
    pos_order_ids = sale_invoices.mapped("pos_order_id")

    pos_order = self.env['pos.order'].search(
        [('id', 'in', pos_order_ids.ids)]
    ).filtered(lambda r: r.store_id.is_post_bkav == True)

    lines = self.env['pos.order.line'].search([
        ('order_id', 'in', pos_order.ids),
        ('qty', '>', 0)
    ])
    stores = pos_order.mapped("store_id")
    items = {}
    for store in stores:
        lines_store = lines.filtered(lambda r: r.order_id.store_id.id == store.id)
        compare_move_lines(
            self,
            items=items,
            store=store,
            lines=list(lines_store),
            missing_line=[],
            page=0, 
            first_n=0, 
            last_n=1000
        )

    for k, v in items.items():
        res_line = model_line.create(v["line_ids"])
        v["line_ids"] = res_line.ids

    vals_list = list(items.values())

    res = model.create(vals_list)
    return res
