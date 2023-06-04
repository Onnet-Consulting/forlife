from odoo import models, api, tools, _
from odoo.models import fix_import_export_id_paths, PGERROR_TO_OE, _logger
from odoo.tools.lru import LRU
import psycopg2
import psycopg2.extensions
import odoo


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # Override base for new logic import data, import record pass validation and skip error"
    @api.model
    def load(self, fields, data):
        """
        Attempts to load the data matrix, and returns a list of ids (or
        ``False`` if there was an error and no id could be generated) and a
        list of messages.

        The ids are those of the records created and saved (in database), in
        the same order they were extracted from the file. They can be passed
        directly to :meth:`~read`

        :param fields: list of fields to import, at the same index as the corresponding data
        :type fields: list(str)
        :param data: row-major matrix of data to import
        :type data: list(list(str))
        :returns: {ids: list(int)|False, messages: [Message][, lastrow: int]}
        """
        if not self._context.get('import_valid_skip_error'):
            return super(BaseModel, self).load(fields, data)
        else:
            self.env.flush_all()

            # determine values of mode, current_module and noupdate
            mode = self._context.get('mode', 'init')
            current_module = self._context.get('module', '__import__')
            noupdate = self._context.get('noupdate', False)
            # add current module in context for the conversion of xml ids
            self = self.with_context(_import_current_module=current_module)

            cr = self._cr
            sp = cr.savepoint(flush=False)

            fields = [fix_import_export_id_paths(f) for f in fields]
            fg = self.fields_get()

            ids = []
            messages = []

            # list of (xid, vals, info) for records to be created in batch
            batch = []
            batch_xml_ids = set()
            # models in which we may have created / modified data, therefore might
            # require flushing in order to name_search: the root model and any
            # o2m
            creatable_models = {self._name}
            for field_path in fields:
                if field_path[0] in (None, 'id', '.id'):
                    continue
                model_fields = self._fields
                if isinstance(model_fields[field_path[0]], odoo.fields.Many2one):
                    # this only applies for toplevel m2o (?) fields
                    if field_path[0] in (self.env.context.get('name_create_enabled_fieds') or {}):
                        creatable_models.add(model_fields[field_path[0]].comodel_name)
                for field_name in field_path:
                    if field_name in (None, 'id', '.id'):
                        break

                    if isinstance(model_fields[field_name], odoo.fields.One2many):
                        comodel = model_fields[field_name].comodel_name
                        creatable_models.add(comodel)
                        model_fields = self.env[comodel]._fields

            def flush(*, xml_id=None, model=None):
                if not batch:
                    return

                assert not (xml_id and model), \
                    "flush can specify *either* an external id or a model, not both"

                if xml_id and xml_id not in batch_xml_ids:
                    if xml_id not in self.env:
                        return
                if model and model not in creatable_models:
                    return
                # Override here to change data_list
                # Logic
                # full_data_import = [record 1,record 2,record 3,record 4,record 5,record 6,...]
                # error_message_records = [record 1,record 3,record 5]
                # we will remove error records before append to data_list
                error_records = [err.get('record') for err in messages]
                data_list = []
                for xid, vals, info in batch:
                    if info.get('record') not in error_records:
                        data_list.append(dict(xml_id=xid, values=vals, info=info, noupdate=noupdate))
                batch.clear()
                batch_xml_ids.clear()

                # try to create in batch
                try:
                    with cr.savepoint():
                        recs = self._load_records(data_list, mode == 'update')
                        ids.extend(recs.ids)
                    return
                except psycopg2.InternalError as e:
                    # broken transaction, exit and hope the source error was already logged
                    if not any(message['type'] == 'error' for message in messages):
                        info = data_list[0]['info']
                        messages.append(dict(info, type='error', message=_(u"Unknown database error: '%s'", e)))
                    return
                except Exception:
                    pass

                errors = 0
                # try again, this time record by record
                for i, rec_data in enumerate(data_list, 1):
                    try:
                        with cr.savepoint():
                            rec = self._load_records([rec_data], mode == 'update')
                            ids.append(rec.id)
                    except psycopg2.Warning as e:
                        info = rec_data['info']
                        messages.append(dict(info, type='warning', message=str(e)))
                    except psycopg2.Error as e:
                        info = rec_data['info']
                        messages.append(dict(info, type='error', **PGERROR_TO_OE[e.pgcode](self, fg, info, e)))
                        # Failed to write, log to messages, rollback savepoint (to
                        # avoid broken transaction) and keep going
                        errors += 1
                    except Exception as e:
                        _logger.debug("Error while loading record", exc_info=True)
                        info = rec_data['info']
                        message = (_(u'Unknown error during import:') + u' %s: %s' % (type(e), e))
                        moreinfo = _('Resolve other errors first')
                        messages.append(dict(info, type='error', message=message, moreinfo=moreinfo))
                        # Failed for some reason, perhaps due to invalid data supplied,
                        # rollback savepoint and keep going
                        errors += 1
                    # comment here to avoid interupt check error records
                    # if errors >= 10 and (errors >= i / 10):
                    #     messages.append({
                    #         'type': 'warning',
                    #         'message': _(u"Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors.")
                    #     })
                    #     break

            # make 'flush' available to the methods below, in the case where XMLID
            # resolution fails, for instance
            flush_recordset = self.with_context(import_flush=flush, import_cache=LRU(1024))

            # TODO: break load's API instead of smuggling via context?
            limit = float('inf')
            extracted = flush_recordset._extract_records(fields, data, log=messages.append, limit=limit)

            converted = flush_recordset._convert_records(extracted, log=messages.append)

            info = {'rows': {'to': -1}}
            for id, xid, record, info in converted:
                if self.env.context.get('import_file') and self.env.context.get('import_skip_records'):
                    if any([record.get(field) is None for field in self.env.context['import_skip_records']]):
                        continue
                if xid:
                    xid = xid if '.' in xid else "%s.%s" % (current_module, xid)
                    batch_xml_ids.add(xid)
                elif id:
                    record['id'] = id
                batch.append((xid, record, info))

            flush()
            # Remove code in here, because if have error records, odoo will be rollback save point
            # if any(message['type'] == 'error' for message in messages):
            #     sp.rollback()
            #     ids = False
            #     # cancel all changes done to the registry/ormcache
            #     self.pool.reset_changes()
            sp.close(rollback=False)

            nextrow = info['rows']['to'] + 1
            if nextrow < limit:
                nextrow = 0
            return {
                'ids': ids,
                'messages': messages,
                'nextrow': nextrow,
            }
