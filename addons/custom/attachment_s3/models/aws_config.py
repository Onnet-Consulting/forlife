from odoo import api, exceptions, models, fields, _
import logging

_logger = logging.getLogger(__name__)

try:
    import boto3
except ImportError as err:  # pragma: no cover
    _logger.debug(err)


def _load_aws_regions():
    _logger.info("Loading available AWS regions")
    session = boto3.session.Session()
    return [
        (region, region.replace("-", " ").capitalize())
        for region in session.get_available_regions("s3")
    ]

AWS_REGIONS = _load_aws_regions()

class AwsConfig(models.Model):
    _name = 'aws.config'
    _rec_name = 'aws_name'

    aws_name = fields.Char(string=_("Name"))
    active = fields.Boolean(string=_("Active"))
    aws_host = fields.Char(
        string=_("AWS Host"),
        help="If you are using a different host than standard AWS ones, "
             "eg: Exoscale",
    )
    aws_bucket = fields.Char(string=_("Bucket"))
    aws_access_key_id = fields.Char(string=_("Access Key ID"))
    aws_secret_access_key = fields.Char(string=_("Secret Access Key"))
    aws_region = fields.Selection(selection="_selection_aws_region", string=_("Region"))

    def _selection_aws_region(self):
        return (
            [("", "None")]
            + AWS_REGIONS
            + [("other", "Empty or Other (Manually specify below)")]
        )

