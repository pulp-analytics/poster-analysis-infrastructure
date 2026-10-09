#!/usr/bin/env python3
"""Downloads an S3 object and appends its raw bytes to a local file.

Used by the state machine's AppendKnownIds step to append known,
human-labeled test ids onto whatever Enumerate's fresh TMDB sample
produced -- avoids fragile nested shell/Python quoting for a one-line
S3-fetch-and-append that boto3 (already in the image) can do directly.

  python3 fetch_and_append.py <bucket> <key> <dest_path>
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
    ap.add_argument("dest", help="local destination path (appended to)")
    args = ap.parse_args()

    try:
        body = boto3.client("s3").get_object(Bucket=args.bucket, Key=args.key)["Body"].read()
    except (BotoCoreError, ClientError) as e:
        sys.exit(f"ERROR: failed to fetch s3://{args.bucket}/{args.key}: {e}")

    try:
        with open(args.dest, "ab") as f:
            f.write(body)
    except OSError as e:
        sys.exit(f"ERROR: failed to append to {args.dest}: {e}")


if __name__ == "__main__":
    main()
