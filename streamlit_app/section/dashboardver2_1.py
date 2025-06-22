import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from streamlit import column_config
from section.utils.helper import save_dataframe_to_db, search_database, highlight_critical_and_edited, identify_critical_columns, CRITICAL_KEYWORDS, is_safe_sql
from section.database import database_page
from section.user import user_page


def show_dashboard():
    # Session State Initialization
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    if 'active_page' not in st.session_state:
        st.session_state.active_page = "Dashboard"
    if 'uploaded_filename' not in st.session_state:
        st.session_state.uploaded_filename = None
    if 'upload_error' not in st.session_state:
        st.session_state.upload_error = None
    if 'original_data' not in st.session_state:
        st.session_state.original_data = None
    if 'original_dtypes' not in st.session_state:
        st.session_state.original_dtypes = None

    page_map = {
    "📶 Dashboard": "Dashboard",
    "🗃️ Database": "Database",
    "👮 User": "User"
    }
    
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Dashboard"
    
    selected = st.sidebar.radio(
        "Select Page",
        options=list(page_map.keys()),
        index=list(page_map.values()).index(st.session_state.active_page)
    )
    
    if page_map[selected] != st.session_state.active_page:
        st.session_state.active_page = page_map[selected]

    st.sidebar.title("Upload File")
    uploaded_file = st.sidebar.file_uploader("Choose a file", type=["csv", "xlsx", "txt", "json"])

    if uploaded_file and uploaded_file != st.session_state.get('uploaded_filename'):
        st.session_state.upload_error = None
        # Clear previous data if new file is selected
        st.session_state.uploaded_data = None
        st.session_state.uploaded_filename = None

    if uploaded_file:
        @st.cache_data(show_spinner="Loading file...")
        def load_file(uploaded_file):
            try:
                if uploaded_file.size == 0:
                    return None, "Uploaded file is empty (0 bytes)"

                file_ext = uploaded_file.name.split('.')[-1].lower()

                if file_ext == 'csv':
                    try:
                        return pd.read_csv(uploaded_file, low_memory=False), None
                    except UnicodeDecodeError:
                        try:
                            return pd.read_csv(uploaded_file, encoding='latin1', low_memory=False), None
                        except Exception as e:
                            return None, f"CSV Error: {str(e)}"

                elif file_ext == 'xlsx':
                    try:
                        return pd.read_excel(uploaded_file), None
                    except Exception as e:
                        return None, f"Excel Error: {str(e)}"

                elif file_ext == 'txt':
                    try:
                        return pd.read_csv(uploaded_file, delimiter='\t', low_memory=False), None
                    except Exception as e:
                        return None, f"Text File Error: {str(e)}"

                elif file_ext == 'json':
                    try:
                        return pd.read_json(uploaded_file, lines=True), None
                    except Exception as e:
                        return None, f"JSON Error: {str(e)}"

                return None, "Unsupported file format"

            except Exception as e:
                return None, f"Unexpected error: {str(e)}"
        
        # Load file and get both data and error
        data, error = load_file(uploaded_file)
        
        if error:
            st.session_state.upload_error = error
            st.error(f"⚠️ File Error: {error}")  # Show only in main area
            st.session_state.uploaded_data = None
        elif data is not None:
            st.session_state.uploaded_data = data
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.original_data = data.copy()
            st.session_state.original_dtypes = data.dtypes.to_dict()
            st.sidebar.success(f"Loaded {uploaded_file.name}")

    # Main Dashboard
    if st.session_state.active_page == "Dashboard":
        st.write(f"Welcome, {st.session_state.get('username', 'User')}!")
        st.title("📊 Banking Data Dashboard")

        if st.session_state.uploaded_data is not None:
            # Always work with a copy from session state
            df = st.session_state.uploaded_data.copy()

            # --- Memory Optimization ---
            st.subheader("Optimizing Data...")
            with st.spinner("Optimizing data types to reduce memory usage..."):
                original_memory = df.memory_usage(deep=True).sum() / (1024**2)
                optimized_df = df.copy()

                for col in optimized_df.columns:
                    if optimized_df[col].dtype == 'object':
                        if optimized_df[col].nunique() < 0.5 * len(optimized_df[col]):
                            try:
                                optimized_df[col] = optimized_df[col].astype('category')
                            except:
                                pass
                    elif optimized_df[col].dtype in ['int64', 'float64']:
                        try:
                            optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='integer')
                        except:
                            try:
                                optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')
                            except:
                                pass

                optimized_memory = optimized_df.memory_usage(deep=True).sum() / (1024**2)
                st.success(f"Memory usage reduced from {original_memory:.2f} MB to {optimized_memory:.2f} MB.")
                st.session_state.uploaded_data = optimized_df.copy()
                edited_df = st.session_state.uploaded_data.copy()

                # Pie Chart for Data Types
                data_types = optimized_df.dtypes.value_counts().reset_index()
                data_types.columns = ['Type', 'Count']

                type_map = {
                    'int64': 'Integer64',
                    'int32': 'Integer32',
                    'int16': 'Integer16',
                    'int8': 'Integer8',
                    'float64': 'Float64',
                    'float32': 'Float32',
                    'float16': 'Float16',
                    'object': 'String',
                    'datetime64[ns]': 'Date',
                    'bool': 'Boolean',
                    'category': 'Categorical',
                }

                type_description_map = {
                    'Integer64': '64-bit Integer: Large whole numbers',
                    'Integer32': '32-bit Integer: Smaller whole numbers',
                    'Integer16': '16-bit Integer: Small-range integers',
                    'Integer8': '8-bit Integer: Very small integers',
                    'Float64': '64-bit Float: Precise decimal values',
                    'Float32': '32-bit Float: Less precise decimals',
                    'Float16': '16-bit Float: Low-precision decimals',
                    'String': 'Text or mixed-type values',
                    'Date': 'Datetime values with nanosecond precision',
                    'Boolean': 'True or False values',
                    'Categorical': 'Discrete categories or labels',
                    'Other': 'Unrecognized or custom data type',
                }

                # Map types to readable names
                data_types['Type'] = data_types['Type'].astype(str).map(type_map).fillna('Other')

                # Add descriptions for hover
                data_types['Description'] = data_types['Type'].map(type_description_map)

                # Create pie chart with descriptions on hover
                fig_pie = px.pie(
                    data_types,
                    names='Type',
                    values='Count',
                    title='Data Types',
                    hover_data=['Description']
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')

            # Metrics
            null_values = optimized_df.isnull().sum().sum()
            total_rows = len(optimized_df)
            total_columns = len(optimized_df.columns)
            total_dtypes = optimized_df.dtypes.nunique()

            # Bar Chart for Uniqueness
            total_summary = pd.DataFrame({
                'Column': optimized_df.columns,
                'Count': optimized_df.nunique()
            })
            fig_bar = px.bar(total_summary, x='Column', y='Count', title='Total Summary of Data')

            # Layout
            col1, col2, col3 = st.columns([3, 1, 3])
            col1.plotly_chart(fig_pie, use_container_width=True)
            st.plotly_chart(fig_bar, use_container_width=True)
            col2.metric("NULL Values", null_values)
            col2.metric("Rows", total_rows)
            col2.metric("Columns", total_columns)
            col2.metric("Data Types", total_dtypes)

            numeric_summary = df.describe().T[['mean', 'std', 'min', 'max']]
            col3.subheader("📊 Numeric Summary")
            col3.dataframe(numeric_summary)

            table_data = pd.DataFrame({
                "Data Type": [type_map.get(str(dtype), str(dtype)) for dtype in optimized_df.dtypes],
                "Unique Values": optimized_df.nunique(),
                "Missing Values": optimized_df.isnull().sum(),
                "Example Value": optimized_df.iloc[0] if not optimized_df.empty else None # Handle empty DataFrame
            })

            st.subheader("📋 Data Dictionary")
            st.dataframe(table_data)

            # **Update original_data before displaying the editor**
            st.session_state.original_data = st.session_state.uploaded_data.copy()
            # Identify critical columns
            critical_cols_to_highlight = identify_critical_columns(df.columns, CRITICAL_KEYWORDS)
            st.write(f"Identified potential critical columns: {critical_cols_to_highlight}") # For debugging

            col_configs = {}
            for col in optimized_df.columns:
                if col in critical_cols_to_highlight:
                    col_configs[col] = column_config.Column(
                        label=f"⚠️ {col}", 
                        help="This column is critical",
                        disabled=False,
                    )
                else:
                    col_configs[col] = column_config.Column(label=col)

            st.subheader("🧹 Clean & Edit Your Data")  
            edited_df = st.data_editor(  
                st.session_state.uploaded_data,  
                use_container_width=True,  
                num_rows="dynamic",  
                key="editable_table",  
                column_config=col_configs  
            )  

            # Check if data was edited by comparing with session state
            if not edited_df.equals(st.session_state.uploaded_data):
                st.session_state.uploaded_data = edited_df.copy()

                # Auto-save to database  
                table_name = st.session_state.uploaded_filename.split('.')[0]  
                save_successful, message = save_dataframe_to_db(st.session_state.uploaded_data, table_name)  
                if save_successful:  
                    st.success("Changes saved to database automatically")  
                else:  
                    st.error(f"Error saving changes: {message}")

            if st.session_state.uploaded_data is not None:
                df = st.session_state.uploaded_data

                # Detect columns with nulls
                null_cols = df.columns[df.isnull().any()].tolist()

                if null_cols:
                    st.subheader("Null Value Imputation Options")

                    selected_col = st.selectbox("Select column to impute nulls", null_cols)
                    col_dtype = df[selected_col].dtype  # Define dtype here safely

                    option = st.radio(
                        f"How do you want to replace nulls in '{selected_col}'?",
                        ('Mean', 'Zero', 'Custom Value')
                    )

                    replacement = None  # Initialize

                    if option == 'Custom Value':
                        custom_val = st.text_input("Enter your custom replacement value:")

                        if custom_val.strip() == "":
                            st.warning("Please enter a value.")
                        else:
                            # Try to convert custom_val to appropriate type based on col_dtype
                            try:
                                if np.issubdtype(col_dtype, np.integer):
                                    val_float = float(custom_val)
                                    if val_float.is_integer():
                                        replacement = int(val_float)
                                    else:
                                        st.warning("Float will be truncated to int.")
                                        replacement = int(val_float)
                                elif np.issubdtype(col_dtype, np.floating):
                                    replacement = float(custom_val)
                                else:
                                    # For non-numeric columns, keep as string
                                    replacement = custom_val
                            except ValueError:
                                st.error("Custom value must match the column data type.")

                    if st.button("Replace Nulls"):
                        if option == 'Mean':
                            if np.issubdtype(col_dtype, np.number):
                                replacement = df[selected_col].mean()
                            else:
                                st.error("Mean imputation only available for numeric columns.")
                                replacement = None
                        elif option == 'Zero':
                            if np.issubdtype(col_dtype, np.number):
                                replacement = 0
                            else:
                                st.error("Zero replacement only available for numeric columns.")
                                replacement = None
                        # For custom value, replacement was already set above

                        if replacement is not None:
                            df[selected_col].fillna(replacement, inplace=True)
                            st.success(f"Null values in '{selected_col}' replaced with {replacement}")

                            # Save back to session state
                            st.session_state.uploaded_data = df.copy()

                            # Save to DB immediately
                            table_name = st.session_state.uploaded_filename.split('.')[0]
                            save_successful, message = save_dataframe_to_db(df, table_name)
                            if save_successful:
                                st.success("Updated data saved to database.")
                            else:
                                st.error(f"Error saving changes: {message}")

            # Column Operations
            st.subheader("🛠️ Column Operations")

            # Change Data Type
            with st.expander("🔀 Change Column Data Type"):
                col_to_change = st.selectbox("Select column to change:", edited_df.columns)
                current_dtype = str(edited_df[col_to_change].dtype)
                
                # Simplified dtype options and index finding
                dtype_options = ['int64', 'int32', 'int16', 'int8', 'float64', 'float32', 'object', 'category', 'datetime64[ns]']
                current_index = dtype_options.index(current_dtype) if current_dtype in dtype_options else 0
                
                new_dtype = st.selectbox("Select new data type:", dtype_options, index=current_index)
                
                change_type_button = st.button("💾 Apply Data Type Change")
                
                if change_type_button:
                    try:
                        # Create a copy of the DataFrame to modify
                        modified_df = edited_df.copy()
                        
                        if new_dtype == 'datetime64[ns]':
                            # Use pd.to_datetime and assign back to column
                            modified_df[col_to_change] = pd.to_datetime(
                                modified_df[col_to_change], 
                                errors='coerce'
                            )
                        else:
                            # Direct assignment for other types
                            modified_df[col_to_change] = modified_df[col_to_change].astype(new_dtype)
                        
                        # Update the session state with the modified DataFrame
                        st.session_state.uploaded_data = modified_df
                        st.success(f"Data type of '{col_to_change}' changed to '{new_dtype}'.")
                        
                    except Exception as e:
                        st.error(f"Error changing data type: {e}")

            # Delete Columns
            with st.expander("🗑️ Delete Column"):
                columns_to_delete = st.multiselect("Select columns to delete:", st.session_state.uploaded_data.columns)
                if st.button("Delete Selected Columns"):
                    if columns_to_delete:
                        try:
                            st.session_state.uploaded_data = st.session_state.uploaded_data.drop(columns=columns_to_delete)
                            # Save immediately after deletion
                            table_name = st.session_state.uploaded_filename.split('.')[0]
                            save_successful, message = save_dataframe_to_db(st.session_state.uploaded_data, table_name)
                            if save_successful:
                                st.success(f"Deleted columns and saved: {', '.join(columns_to_delete)}")
                            else:
                                st.error(f"Error saving after deletion: {message}")
                        except Exception as e:
                            st.error(f"Error: {e}")
                   
            st.markdown("### 📦 Final Edited Data")

            # Always get the current and original data from session state
            final_df = st.session_state.get('uploaded_data')
            original_df = st.session_state.get('original_data')

            if final_df is not None and original_df is not None:
                # Align columns and indexes
                original_df = original_df[final_df.columns]
                final_df.reset_index(drop=True, inplace=True)
                original_df.reset_index(drop=True, inplace=True)

                if final_df.shape[0] == original_df.shape[0]:
                    styled_df = final_df.style.apply(
                        lambda x: highlight_critical_and_edited(final_df, original_df, critical_cols_to_highlight),
                        axis=None
                    )
                    st.write(styled_df)
                else:
                    st.dataframe(final_df, use_container_width=True)
            else:
                st.warning("No data found. Please upload a file.")

            st.markdown("### 📥 Export Data")
            csv = final_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "updated_data.csv", "text/csv", key="downl")
                        
            
            # Search SQL
            st.subheader("🔍 Search Database")
            search_input = st.text_area("Enter SQL query", key="database_search_input", height=150)

            if search_input:
                user_role = st.session_state.get("user_role", "user")  # Default to 'user' if not set

                if is_safe_sql(search_input, user_role):
                    try:
                        results_df = search_database(search_input)
                        if results_df is not None:
                            st.dataframe(results_df)
                        else:
                            st.info("No data returned for the query.")
                    except Exception as e:
                        st.error(f"Query Error: {e}")
                else:
                    st.error("⚠️ You are not allowed to run this type of SQL command.")

            # Optional Charts Section
            st.sidebar.subheader("Optional Charts")
            final_df = st.session_state.uploaded_data

            if st.sidebar.checkbox("🌡️ Correlation Heatmap"):
                st.subheader("Correlation Heatmap")
                numeric_cols = final_df.select_dtypes(include=['int64', 'float64']).columns
                if len(numeric_cols) > 1:
                    corr = final_df[numeric_cols].corr()
                    fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale="Viridis", title="Correlation Heatmap")
                    st.plotly_chart(fig_corr, use_container_width=True)
                else:
                    st.warning("At least two numeric columns are needed for the correlation heatmap.")

            if st.sidebar.checkbox("📊 Histogram (Frequency Distribution)"):
                st.subheader("Histogram (Frequency Distribution)")
                numeric_cols = final_df.select_dtypes(include=['int64', 'float64']).columns
                if len(numeric_cols) > 0:
                    col_to_hist = st.selectbox("Select numeric column for histogram:", numeric_cols)
                    fig_hist = px.histogram(final_df, x=col_to_hist, title=f"Frequency Distribution of {col_to_hist}")
                    st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.warning("No numeric columns available for the histogram.")

        else:
            st.warning("📂 Upload a file to see the dashboard.")

    # Database Page
    elif st.session_state.active_page == "Database":
        try:
            database_page()
        except ImportError:
            st.error("The 'database.py' file or the 'database_page' function was not found.")

    # User Page
    elif st.session_state.active_page == "User":
        user_page()
