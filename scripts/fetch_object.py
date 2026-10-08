#!/usr/bin/env python3
"""Downloads an S3 object to a local path, overwriting whatever's there.

Different from fetch_and_append.py (which appends, for the
AppendKnownIds test step): this is for static reference data -- e.g.
gate 2's pre-filtered adult_tconsts list -- that should be refreshed
in full on every run, not accumulated onto across reruns of the same
EFS-persisted path.

  python3 fetch_object.py <bucket> <key> <dest_path>
"""
from __future__ import annotations

import argparse
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bucket", help="source S3 bucket name")
    ap.add_argument("key", help="source S3 object key")
    ap.add_argument("dest", help="local destination path (overwritten)")
    args = ap.parse_args()

    try:
        body = boto3.client("s3").get_object(Bucket=args.bucket, Key=args.key)["Body"].read()
    except (BotoCoreError, ClientError) as e:
        sys.exit(f"ERROR: failed to fetch s3://{args.bucket}/{args.key}: {e}")

    try:
        with open(args.dest, "wb") as f:
            f.write(body)
    except OSError as e:
        sys.exit(f"ERROR: failed to write {args.dest}: {e}")


if __name__ == "__main__":
    main()
