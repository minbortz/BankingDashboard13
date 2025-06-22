# BankingDashboard

# 🏦 Real-Time Data Validation and Banking Dashboard

This project is a **Streamlit-based dashboard** that enables users to upload various banking data formats, validate and clean the data, visualize key insights, and optionally save the data to a MySQL database.

---

## 🚀 Features

- 📁 **Multi-Format File Upload**
  - Supports TXT, Excel, JSON and CSV
  - Converts all formats to standardized CSV for processing

- 🧹 **Automated Data Cleaning**
  - Handles missing values, inconsistent data types, and formatting issues

- 📊 **Interactive Dashboard**
  - Displays:
    - Data type summary
    - Numeric column count
    - Null value count
    - Full data table
    - Default bar chart
  - Optional: Colleration Heatmap, Histogram (Frequency Distribution)

- 🔍 **Search and Query**
  - Popup search feature to find and extract specific entries

- 🗃️ **Database Integration**
  - Connects to MySQL (hosted on AivenCloud)
  - Allows saving of cleaned data to a database
  - Supports user and admin authentication

- 👥 **User/Admin Authentication**
  - Signup and login system for different user roles
  - Session-based access control

---

## 📂 Project Structure

```plaintext
streamlit_app                
├── streamlit_app.py/
│   ├── section/
│   │   ├── dashboard.py         # Dashboard logic and visualizations
│   │   ├── database.py          # Database page
│   │   ├── user.py              # User login/signup interface
│   │   └── utils/
│   │       └── helper.py        # Helper functions (validation, cleaning, etc.)

## 🔗 Live Demo

You can view the live dashboard by clicking this link:  
👉 [**Open Banking Dashboard**](https://bankingdashboard13-mhklc.streamlit.app/)
