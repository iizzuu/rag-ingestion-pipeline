import os
import logging
from datetime import datetime

from aws_xray_sdk.core import xray_recorder, patch_all
patch_all()

import boto3
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

from chunker import chunk_document
from embedder import embed_chunks
from store import get_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

s3 = boto3.client("s3")
dynamo = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-2"))
table = dynamo.Table(os.environ["DYNAMODB_TABLE"])

_pdf_opts = PdfPipelineOptions()
_pdf_opts.do_ocr = False

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=_pdf_opts)}
)


def _update_status(document_id: str, status: str, extra: dict = None):
    attrs = {
        ":s": status,
        ":u": datetime.utcnow().isoformat(),
    }
    expr = "SET #st = :s, updated_at = :u"
    names = {"#st": "status"}

    if extra:
        for key, val in extra.items():
            attrs[f":{key}"] = val
            expr += f", {key} = :{key}"

    table.update_item(
        Key={"document_id": document_id},
        UpdateExpression=expr,
        ExpressionAttributeValues=attrs,
        ExpressionAttributeNames=names,
    )


def run():
    bucket      = os.environ["BUCKET"]
    key         = os.environ["KEY"]
    document_id = os.environ["DOCUMENT_ID"]
    filename    = os.environ.get("FILENAME", key.split("/")[-1])

    file_path = f"/tmp/{document_id}_{filename}"

    try:
        log.info("Downloading s3://%s/%s", bucket, key)
        s3.download_file(bucket, key, file_path)
        result = converter.convert(file_path)
    except Exception as e:
        _update_status(document_id, "failed", {"error": str(e)})
        raise RuntimeError(f"Conversion failed for {document_id}: {e}") from e
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    try:
        chunks = chunk_document(result.document, document_id, max_tokens=int(os.environ.get("MAX_TOKENS", "512")))
        if not chunks:
            raise RuntimeError(f"No chunks produced for {document_id}")

        embedded = embed_chunks(chunks)
        store = get_store()
        store.upsert_chunks(embedded)

        _update_status(document_id, "processed", {"chunk_count": str(len(embedded))})
        log.info("Done — %d chunks for %s", len(embedded), document_id)

    except Exception as e:
        _update_status(document_id, "failed", {"error": str(e)})
        raise


if __name__ == "__main__":
    run()
