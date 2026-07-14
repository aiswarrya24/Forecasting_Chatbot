
from pymongo import MongoClient
from datetime import datetime, timedelta
from .config import MONGO_DB_CONNECTION_STRING, DB_NAME, SALES_COLLECTION
import os # Import os for environment variable access

# Initialize MongoDB connection (using the corrected variable name)
client = None # Initialize client to None
db = None
sales_collection = None # Initialize sales_collection to None

try:
    # Use os.getenv to fetch the connection string from .env, if it exists
    # Otherwise, fall back to the one in config.py
    actual_mongo_uri = os.getenv("MONGO_DB_CONNECTION_STRING", MONGO_DB_CONNECTION_STRING)
    print(f"DEBUG: Attempting to connect to MongoDB with URI: {actual_mongo_uri}")
    client = MongoClient(actual_mongo_uri)
    db = client[DB_NAME]
    sales_collection = db[SALES_COLLECTION]
    # The ping command is a simple way to check if the server is accessible
    client.admin.command('ping')
    print("DEBUG: Successfully connected to MongoDB!")
except Exception as e:
    print(f"ERROR: Failed to connect to MongoDB: {e}")
    # client, db, sales_collection remain None if connection fails
    pass # Continue with the application, but functions will handle None

def get_sales_data(tname: str = None, gname: str = None, start_date: datetime = None, end_date: datetime = None, pname: str = None, all_time: bool = False, include_pname: bool = False, include_tname: bool = False) -> list[dict]:
    """
    Fetches sales data from MongoDB based on tenant, group, date range, and product name.
    Args:
        tname (str, optional): Tenant name. Defaults to None.
        gname (str, optional): Group name. Defaults to None.
        start_date (datetime, optional): Start date for the query. Defaults to None.
        end_date (datetime, optional): End date for the query. Defaults to None.
        pname (str, optional): Product name filter. Defaults to None.
        all_time (bool, optional): If True, ignores start_date and end_date to fetch all records.
                                    Defaults to False.
        include_pname (bool, optional): If True, includes 'pname' in the returned documents.
                                        Defaults to False.
        include_tname (bool, optional): If True, includes 'tname' in the returned documents.
                                        Defaults to False.
    Returns:
        list[dict]: A list of sales records. Each record is a dictionary.
    """
    if sales_collection is None:
        print("ERROR: Sales collection not initialized due to MongoDB connection failure.")
        return []

    query = {}

    if all_time:
        # If all_time is True, then start_date and end_date are ignored
        pass
    else:
        # Apply date range filter only if not all_time and dates are provided
        if start_date and end_date:
            query['date'] = {'$gte': start_date, '$lte': end_date}
        elif start_date:
            query['date'] = {'$gte': start_date}
        elif end_date:
            query['date'] = {'$lte': end_date}

    if tname:
        query['tname'] = tname
    if gname:
        query['gname'] = gname
    if pname:
        query['pname'] = pname

    projection = {'_id': 0, 'date': 1, 'sales': 1}
    if include_pname:
        projection['pname'] = 1
    if include_tname:
        projection['tname'] = 1
    if gname: # If querying by group, tname should always be included for analysis
        projection['tname'] = 1

    print(f"DEBUG: Executing sales query: {query}, projection: {projection}")
    result = list(sales_collection.find(query, projection))
    print(f"DEBUG: Sales query returned {len(result)} records.")
    return result

def get_all_tenants_sales(start_date: datetime = None, end_date: datetime = None) -> list[dict]:
    """
    Fetches sales data for all tenants. Can be filtered by date range.
    Args:
        start_date (datetime, optional): Start date for the query. Defaults to None.
        end_date (datetime, optional): End date for the query. Defaults to None.
    Returns:
        list[dict]: A list of sales records including tname and gname.
    """
    if sales_collection is None:
        print("ERROR: Sales collection not initialized due to MongoDB connection failure.")
        return []

    query = {}
    if start_date and end_date:
        query['date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['date'] = {'$gte': start_date}
    elif end_date:
        query['date'] = {'$lte': end_date}

    # Always include tname, gname, sales, and date for all-tenant queries
    projection = {'_id': 0, 'tname': 1, 'gname': 1, 'date': 1, 'sales': 1, 'pname': 1}
    print(f"DEBUG: Executing all tenants sales query: {query}, projection: {projection}")
    result = list(sales_collection.find(query, projection))
    print(f"DEBUG: All tenants sales query returned {len(result)} records.")
    return result

def tenant_exists(tname: str) -> bool:
    """Checks if a tenant exists by finding any sales record for that tenant."""
    if sales_collection is None:
        print("ERROR: Sales collection not initialized due to MongoDB connection failure.")
        return False
    
    print(f"DEBUG: Checking if tenant '{tname}' exists in '{DB_NAME}.{SALES_COLLECTION}' (by finding any sale record)")
    # Check if any document in the sales collection has this tname
    count = sales_collection.count_documents({"tname": tname})
    print(f"DEBUG: Tenant exists check for '{tname}' returned count: {count}")
    return count > 0

def get_tenant_gname(tname: str) -> str | None:
    """Retrieves the group name for a given tenant from the sales collection."""
    if sales_collection is None:
        print("ERROR: Sales collection not initialized due to MongoDB connection failure.")
        return None

    print(f"DEBUG: Fetching group name for tenant '{tname}' from sales collection")
    # Find one document for the tenant and get its gname
    tenant_sale_record = sales_collection.find_one({"tname": tname}, {"_id": 0, "gname": 1})
    gname = tenant_sale_record.get("gname") if tenant_sale_record else None
    print(f"DEBUG: Group name for '{tname}' is: {gname}")
    return gname
