import datetime

from odoo import api, fields, models, _
from odoo.addons.base_import.models.base_import import ImportValidationError, _logger
from odoo.tools import config, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat
import psycopg2

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

class Import(models.TransientModel):
    _inherit = "base_import.import"

    # Override this function for additional context for func load()
    def execute_import(self, fields, columns, options, dryrun=False):
        if not options.get('import_valid_skip_error'):
            return super(Import, self).execute_import(fields, columns, options, dryrun=dryrun)
        else:
            """ Actual execution of the import
    
            :param fields: import mapping: maps each column to a field,
                           ``False`` for the columns to ignore
            :type fields: list(str|bool)
            :param columns: columns label
            :type columns: list(str|bool)
            :param dict options:
            :param bool dryrun: performs all import operations (and
                                validations) but rollbacks writes, allows
                                getting as much errors as possible without
                                the risk of clobbering the database.
            :returns: A list of errors. If the list is empty the import
                      executed fully and correctly. If the list is
                      non-empty it contains dicts with 3 keys:
    
                      ``type``
                        the type of error (``error|warning``)
                      ``message``
                        the error message associated with the error (a string)
                      ``record``
                        the data which failed to import (or ``false`` if that data
                        isn't available or provided)
            :rtype: dict(ids: list(int), messages: list({type, message, record}))
            """
            self.ensure_one()
            self._cr.execute('SAVEPOINT import')

            try:
                input_file_data, import_fields = self._convert_import_data(fields, options)
                # Parse date and float field
                input_file_data = self._parse_import_data(input_file_data, import_fields, options)
            except ImportValidationError as error:
                return {'messages': [error.__dict__]}

            _logger.info('importing %d rows...', len(input_file_data))

            import_fields, merged_data = self._handle_multi_mapping(import_fields, input_file_data)

            if options.get('fallback_values'):
                merged_data = self._handle_fallback_values(import_fields, merged_data, options['fallback_values'])

            name_create_enabled_fields = options.pop('name_create_enabled_fields', {})
            import_limit = options.pop('limit', None)
            model = self.env[self.res_model].with_context(
                import_file=True,
                name_create_enabled_fields=name_create_enabled_fields,
                import_set_empty_fields=options.get('import_set_empty_fields', []),
                import_skip_records=options.get('import_skip_records', []),
                import_valid_skip_error=options.get('import_valid_skip_error'),  # override in here
                _import_limit=import_limit)
            import_result = model.load(import_fields, merged_data)
            _logger.info('done')

            # If transaction aborted, RELEASE SAVEPOINT is going to raise
            # an InternalError (ROLLBACK should work, maybe). Ignore that.
            # TODO: to handle multiple errors, create savepoint around
            #       write and release it in case of write error (after
            #       adding error to errors array) => can keep on trying to
            #       import stuff, and rollback at the end if there is any
            #       error in the results.
            try:
                if dryrun:
                    self._cr.execute('ROLLBACK TO SAVEPOINT import')
                    # cancel all changes done to the registry/ormcache
                    self.pool.clear_caches()
                    self.pool.reset_changes()
                else:
                    self._cr.execute('RELEASE SAVEPOINT import')
            except psycopg2.InternalError:
                pass

            # Insert/Update mapping columns when import complete successfully
            if import_result['ids'] and options.get('has_headers'):
                BaseImportMapping = self.env['base_import.mapping']
                for index, column_name in enumerate(columns):
                    if column_name:
                        # Update to latest selected field
                        mapping_domain = [('res_model', '=', self.res_model), ('column_name', '=', column_name)]
                        column_mapping = BaseImportMapping.search(mapping_domain, limit=1)
                        if column_mapping:
                            if column_mapping.field_name != fields[index]:
                                column_mapping.field_name = fields[index]
                        else:
                            BaseImportMapping.create({
                                'res_model': self.res_model,
                                'column_name': column_name,
                                'field_name': fields[index]
                            })
            if 'name' in import_fields:
                index_of_name = import_fields.index('name')
                skipped = options.get('skip', 0)
                # pad front as data doesn't contain anythig for skipped lines
                r = import_result['name'] = [''] * skipped
                # only add names for the window being imported
                r.extend(x[index_of_name] for x in input_file_data[:import_limit])
                # pad back (though that's probably not useful)
                r.extend([''] * (len(input_file_data) - (import_limit or 0)))
            else:
                import_result['name'] = []

            skip = options.get('skip', 0)
            # convert load's internal nextrow to the imported file's
            if import_result['nextrow']:  # don't update if nextrow = 0 (= no nextrow)
                import_result['nextrow'] += skip
            import_result['file_length'] = len(merged_data)  # get length data

            return import_result

    def _read_xlsx(self, options):
        if options.get('import_valid_skip_error', False) and self.res_model == "stock.picking":
            return self._read_xlsx_stock_picking(options)
        res = super(Import, self)._read_xlsx(options)
        return res

    def _read_xlsx_stock_picking(self, options):
        book = xlrd.open_workbook(file_contents=self.file or b'')
        sheets = options['sheets'] = book.sheet_names()
        sheet = options['sheet'] = options.get('sheet') or sheets[0]
        return self._read_xls_book_stock_picking(book, sheet)

    def _read_xls_book_stock_picking(self, book, sheet_name):

        sheet = book.sheet_by_name(sheet_name)
        rows = []
        cols_picking = []
        for rowx, row in enumerate(map(sheet.row, range(1)), 1):
            for colx, cell in enumerate(row, 1):
                if 'Dịch chuyển kho' not in str(cell.value):
                    cols_picking.append(colx)

        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if rowx > 2 and colx in cols_picking:
                    cell.value = ""
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value)
                        if is_float
                        else str(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if is_datetime
                        else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    if cell.value:
                        values.append(u'True' if cell.value else u'False')
                    else:
                        values.append(cell.value)
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s") % {
                            'row': rowx,
                            'col': colx,
                            'cell_value': xlrd.error_text_from_code.get(cell.value,
                                                                        _("unknown error code %s", cell.value))
                        }
                    )
                else:
                    values.append(cell.value)
            if any(x for x in values if x.strip()):
                rows.append(values)

        # return the file length as first value
        return sheet.nrows, rows

