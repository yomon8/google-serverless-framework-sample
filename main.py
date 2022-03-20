import os
from typing import List, Dict, Any, Iterable

from google.cloud import storage
from google.cloud import bigquery


GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = os.environ["GCP_LOCATION"]
BQ_TABLE_ID = os.environ["BQ_TABLE_ID"]
OBJECT_CHARSET = os.environ["OBJECT_CHARSET"]
FIELD_DELIMITER = os.environ["FIELD_DELIMITER"]

schema = [
    bigquery.SchemaField("name", "STRING"),
    bigquery.SchemaField("no", "INT64"),
    bigquery.SchemaField("date", "DATE"),
]


def _load_gcs_obj(bucket: str, object: str, charset: str) -> str:
    gcs_cli = storage.Client()
    bucket = gcs_cli.get_bucket(bucket)
    src_obj_str = bucket.blob(object).download_as_string().decode(charset)
    return src_obj_str


def _convert_object(
    object_str: str, separator: str, schema: List[bigquery.SchemaField]
):
    rows = []
    for r in object_str.splitlines():
        cols = r.split(separator)
        if len(cols) == len(schema):
            row = dict()
            for sf, v in zip(schema, cols):
                row[sf.name] = v
            rows.append(row)
        else:
            print(f"ignored row -> {cols}")
    return rows


def _load_bq(
    bq_table_id: str, rows: Iterable[Dict[str, Any]], schema: List[bigquery.SchemaField]
) -> bigquery.LoadJob:
    bq_job_config = bigquery.LoadJobConfig(
        schema=schema,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    load_job = bigquery.Client().load_table_from_json(
        json_rows=rows, destination=bq_table_id, location=GCP_LOCATION, job_config=bq_job_config
    )
    return load_job


def handler(event, context):
    print(f"Start Event -> {event}")
    bucket, object = event["bucket"], event["name"]
    object_str = _load_gcs_obj(bucket=bucket, object=object, charset=OBJECT_CHARSET)
    rows = _convert_object(
        object_str=object_str, separator=FIELD_DELIMITER, schema=schema
    )
    if not rows:
        print("No data to load.")
        return
    load_job = _load_bq(bq_table_id=BQ_TABLE_ID, rows=rows, schema=schema)
    print(f"Job Result -> {load_job.result()}")
