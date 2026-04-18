import os


def get_action_catalogs_table():
    import boto3

    table_name = os.environ.get("ACTION_CATALOGS_TABLE", "ActionCatalogs")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)
