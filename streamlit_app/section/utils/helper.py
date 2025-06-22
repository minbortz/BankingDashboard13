import logging
import pandas as pd
from sqlalchemy import create_engine, text
from typing import Optional
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_config():
    """Load database config exclusively from Streamlit secrets."""
    try:
        # Check if st.secrets exists and has the db_credentials key
        if hasattr(st, 'secrets') and "db_credentials" in st.secrets:
            logger.info("Loading DB config from Streamlit secrets.")
            return {
                'user': st.secrets.db_credentials.DB_USER,
                'password': st.secrets.db_credentials.DB_PASS,
                'host': st.secrets.db_credentials.DB_HOST,
                'port': st.secrets.db_credentials.DB_PORT,
                'database1': st.secrets.db_credentials.DB_NAME1,
                'database2': st.secrets.db_credentials.DB_NAME2
            }
        else:
            error_msg = "Streamlit secrets 'db_credentials' not found. Ensure secrets.toml is configured correctly for local development, or secrets are set in Streamlit Cloud."
            logger.critical(error_msg)
            raise ValueError(error_msg)
    except Exception as e:
        # Catch any other exceptions during access (e.g., missing specific keys)
        error_msg = f"Error accessing Streamlit secrets: {e}. Please verify your secrets configuration."
        logger.critical(error_msg)
        raise ValueError(error_msg)

# Database Configuration
try:
    db_config = get_db_config()
    DB_USER = db_config['user']
    DB_PASS = db_config['password']
    DB_HOST = db_config['host']
    DB_PORT = db_config['port']
    DB_NAME1 = db_config['database1']
    DB_NAME2 = db_config['database2']

except ValueError as e:
    logger.critical(f"Configuration error: {str(e)}")
    raise # Re-raise to stop the application

# SQLAlchemy Engines
engine1 = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME1}',
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        'connect_timeout': 10,
    }
)

engine2 = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME2}',
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        'connect_timeout': 10,
    }
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
