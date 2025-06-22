import logging
import pandas as pd
import os
from sqlalchemy import create_engine, text
from typing import Optional
from dotenv import load_dotenv 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='../../.env')

def get_env_variable(name: str, default: Optional[str] = None) -> str:
    """Safely get environment variable with validation."""
    value = os.getenv(name, default)
    if value is None:
        error_msg = f"Missing required environment variable: {name}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return value

# Database Configuration with validation
try:
    DB_USER = get_env_variable("DB_USER")
    DB_PASS = get_env_variable("DB_PASS")
    DB_HOST = get_env_variable("DB_HOST")
    DB_PORT = int(get_env_variable("DB_PORT"))  # Convert to integer
    DB_NAME1 = get_env_variable("DB_NAME1")
    DB_NAME2 = get_env_variable("DB_NAME2")
    
    logger.info("Successfully loaded all database configuration")
    
except ValueError as e:
    logger.critical(f"Configuration error: {str(e)}")
    raise

# SQLAlchemy Engines
engine1 = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME1}',
    pool_pre_ping=True,
    pool_recycle=3600
)

engine2 = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME2}',
    pool_pre_ping=True,
    pool_recycle=3600
)

def save_dataframe_to_db(df: pd.DataFrame, table_name: str):
    try:
        # Convert table name to lowercase, safe format
        safe_table_name = table_name.lower().replace(" ", "_")
        df.to_sql(safe_table_name, con=engine1, if_exists='replace', index=False)
        return True, f"Data saved to `{safe_table_name}` successfully."
    except Exception as e:
        return False, str(e)

    
def search_database(query: str) -> Optional[pd.DataFrame]:
    try:
        with engine1.connect() as conn:
            result = conn.execute(text(query))
            if result.returns_rows:
                return pd.DataFrame(result.fetchall(), columns=result.keys())
            else:
                return None
    except Exception as e:
        raise e  # Re-raise the exception to be handled by the caller
 

def insert_user(user_id, username, password, email, timestamp, role):
    query = text("""
        INSERT INTO user_information (userID, username, password, email, signup_time, role)
        VALUES (:userID, :username, :password, :email, :signup_time, :role)
    """)
    with engine2.connect() as conn:
        conn.execute(query, {
            "userID": user_id,
            "username": username,
            "password": password,
            "email": email,
            "signup_time": timestamp,
            "role": role
        })
        conn.commit()

def insert_admin(user_id, username, password, email, timestamp, role):
    query = text("""
        INSERT INTO admin_information (userID, username, password, email, signup_time, role)
        VALUES (:userID, :username, :password, :email, :signup_time, :role)
    """)
    with engine2.connect() as conn:
        conn.execute(query, {
            "userID": user_id,
            "username": username,
            "password": password,
            "email": email,
            "signup_time": timestamp,
            "role": role
        })
        conn.commit()


def get_user_by_username(username):
    query = text("SELECT * FROM user_information WHERE username = :username")
    with engine2.connect() as conn:
        result = conn.execute(query, {"username": username}).fetchone()
        if result:
            return result._mapping
        return None

def get_admin_by_username(username):
    query = text("SELECT * FROM admin_information WHERE username = :username")
    with engine2.connect() as conn:
        result = conn.execute(query, {"username": username}).fetchone()
        if result:
            return result._mapping
        return None
    
CRITICAL_KEYWORDS = [
    # Account/Customer Basics
    "account", "account_number", "account_id", "customer", "customer_id", "client", "user_id",
    "name", "full_name", "email", "phone", "address", "dob", "gender", "national_id",
    
    # Transactions
    "transaction", "transaction_id", "transaction_type", "date", "timestamp", "amount", "currency",
    "status", "reference", "channel", "mode", "description", "remarks",

    # Account Balances & Limits
    "balance", "available_balance", "current_balance", "limit", "overdraft", "credit_limit",

    # Loans & Credit
    "loan", "loan_id", "loan_type", "loan_amount", "interest_rate", "term", "repayment", "emi",
    "installment", "principal", "maturity_date", "collateral", "default", "credit_score",

    # Cards & Payments
    "card", "card_number", "debit", "credit", "payment", "payment_method", "payment_status",

    # Deposits & Withdrawals
    "deposit", "withdrawal", "cash", "cheque", "transfer",

    # Risk & Compliance
    "risk", "fraud", "flag", "sanction", "blacklist", "kyc", "aml", "compliance",

    # Other Useful Fields
    "branch", "ifsc", "swift", "bank_code", "institution", "region", "country", "currency_code",
    "exchange_rate", "fee", "charge", "tax", "vat", "penalty", "commission"
]


def identify_critical_columns(df_columns, keywords=CRITICAL_KEYWORDS):
    """Identifies potential critical columns based on keywords."""
    critical_cols = set()
    for col in df_columns:
        lower_col = col.lower()
        for keyword in keywords:
            if keyword in lower_col:
                critical_cols.add(col)
                break  # Move to the next column once a keyword is found
    return list(critical_cols)

def highlight_critical_and_edited(df, original_df, critical_columns):
    """Highlight edited (green), null (yellow), and critical (orange) cells, in priority order."""

    styles = pd.DataFrame("", index=df.index, columns=df.columns)

    for col in df.columns:
        for i in df.index:
            val_df = df.at[i, col]
            val_orig = original_df.at[i, col] if col in original_df.columns and i in original_df.index else None

            # Start with no style
            style = ""

            # Check if edited
            edited = False
            if val_orig is not None:
                if pd.isnull(val_orig) and pd.isnull(val_df):
                    edited = False
                elif str(val_df) != str(val_orig):
                    edited = True
            elif pd.notnull(val_df):
                edited = True  # New non-null value where there was None

            if edited:
                style = 'background-color: #90ee90; color: black;'  # light green
            elif pd.isnull(val_df):
                style = 'background-color: yellow;'
            elif col in critical_columns:
                style = 'background-color: #ffd8a8; color: black;'  # light orange

            styles.at[i, col] = style

    return styles

DANGEROUS_COMMANDS = ["DROP", "DELETE"]

def is_safe_sql(query: str, user_role: str) -> bool:
    """Check if the query is safe based on user role."""
    query_upper = query.upper()
    for cmd in DANGEROUS_COMMANDS:
        if cmd in query_upper:
            return user_role == "admin"  # Only admin can run dangerous SQL
    return True
