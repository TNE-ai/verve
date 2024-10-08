import json
import yaml
import boto3
import pandas as pd
from PIL import Image
from io import BytesIO
from typing import Dict, List, Optional, Union

# S3 literals
DATA_DIR = "Data"
LATEST = "LATEST"


class TNE:
    def __init__(
        self,
        uid: str = "",
        bucket_name: str = "bp-authoring-files",
        project: Optional[str] = None,
        version: Optional[str] = LATEST,
    ):
        self.uid = uid
        self.bucket_name = bucket_name
        self.client = boto3.client("s3")
        if project:
            self.base_prefix = f"projects/{project}--{version}/{DATA_DIR}"
        else:
            self.base_prefix = f"d/{self.uid}/{DATA_DIR}"
        self.data_list = self.list_data()

    def list_data(self) -> List[str]:
        response = self.client.list_objects_v2(
            Bucket=self.bucket_name, Prefix=self.base_prefix
        )
        data_contents = []
        if "Contents" in response:
            for obj in response["Contents"]:
                filename = obj["Key"].split("data/")[-1]
                if obj["Size"] > 0:
                    data_contents.append(filename)

        return data_contents

    def get_object(self, key: str) -> Union[str, pd.DataFrame, Image, Dict]:
        try:
            file_content = self.get_object_bytes(key)
            if file_content:
                match key.split(".")[-1]:
                    case "txt" | "md" | "out":
                        return file_content.decode("utf-8")
                    case "csv":
                        return pd.read_csv(BytesIO(file_content), encoding="utf-8")
                    case "xlsx":
                        return pd.read_excel(
                            BytesIO(file_content), sheet_name=None, engine="openpyxl"
                        )
                    case "jpg" | "jpeg" | "png":
                        return Image.open(BytesIO(file_content))
                    case "json":
                        return json.loads(file_content.decode("utf-8"))
                    case "yaml" | "yml":
                        return yaml.safe_load(file_content.decode("utf-8"))
                    case _:
                        raise ValueError(
                            f"Unsupported file extension: {key.split('.')[-1]}. Use method get_object_bytes() to access this object."
                        )

        except IOError as io:
            raise io
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise e

    def get_object_bytes(self, key: str) -> bytes:
        try:
            modified_key = f"{self.base_prefix}/{key}"
            file_content = self.client.get_object(
                Bucket=self.bucket_name, Key=modified_key
            )["Body"].read()
            return file_content
        except Exception as e:
            raise IOError(f"Error pulling object from S3: {e}")
