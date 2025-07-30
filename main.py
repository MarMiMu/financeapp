import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")

categories_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": []
    }

if os.path.exists(categories_file):
    with open(categories_file, "r") as f:
        st.session_state.categories = json.load(f)

def save_categories():
    with open(categories_file, "w") as f:
        json.dump(st.session_state.categories, f)

def load_transactions(file):
    try:
        df = pd.read_csv(file)
        # clean up column names
        df.columns = [col.strip() for col in df.columns]
        # remove commas from monetary values and convert to float
        df["Amount"] = df["Amount"].astype(float)\
        # convert date strings to datetime objects
        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d")
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None
    
def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category
    return df

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

def main():
    st.title("Simple Finance Dashboard")
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        if df is not None:
            inflow_df = df[df["Flow"] == "Inflow"].copy()
            outflow_df = df[df["Flow"] == "Outflow"].copy()

            st.session_state.inflow_df = inflow_df.copy()
            st.session_state.outflow_df = outflow_df.copy()

            summary, tab1, tab2 = st.tabs(["Summary","Inflow", "Outflow"])
            with summary:
                st.subheader("Summary")
                st.session_state.inflow_df['Amount'] = st.session_state.inflow_df['Amount'].abs()
                st.session_state.inflow_df = st.session_state.inflow_df[
                    st.session_state.inflow_df["Account Type"] == "Debit"
                ]
                total_inflows = st.session_state.inflow_df['Amount'].sum()
                st.metric("Total Inflows", f"${total_inflows:,.2f} CAD")
                st.session_state.outflow_df = st.session_state.outflow_df[
                    st.session_state.outflow_df["Account Type"] == "Credit"
                ]
                total_payments = st.session_state.outflow_df['Amount'].sum()
                st.metric("Total Payments", f"${total_payments:,.2f} CAD")
                # create a histogram of inflows and outflows with respect to time
                inflow_hist = st.session_state.inflow_df.groupby(st.session_state.inflow_df['Date'].dt.to_period('M'))['Amount'].sum().reset_index()
                outflow_hist = st.session_state.outflow_df.groupby(st.session_state.outflow_df['Date'].dt.to_period('M'))['Amount'].sum().reset_index()
                inflow_hist['Date'] = inflow_hist['Date'].dt.to_timestamp()
                outflow_hist['Date'] = outflow_hist['Date'].dt.to_timestamp()

                # Create the chart
                inflow_hist['Type'] = 'Inflow'
                outflow_hist['Type'] = 'Outflow'
                combined_hist = pd.concat([inflow_hist, outflow_hist])

                fig = px.bar(combined_hist, 
                            x='Date', 
                            y='Amount', 
                            color='Type',
                            barmode='group',
                            title='Monthly Cash Flow')

                # Display in Streamlit
                st.plotly_chart(fig, use_container_width=True)

            with tab1:
                st.session_state.inflow_df['Amount'] = st.session_state.inflow_df['Amount'].abs()
                st.subheader("Your Inflows")
                # get the sum of the Amount column in inflow_df where Account Type = Debit
                st.session_state.inflow_df = st.session_state.inflow_df[
                    st.session_state.inflow_df["Account Type"] == "Debit"
                ]
                total_inflows = st.session_state.inflow_df['Amount'].sum()
                st.metric("Total Inflows", f"${total_inflows:,.2f} CAD")
                edited_df = st.data_editor(
                    st.session_state.inflow_df[["Date", "Details", "Amount", "Category", "Account", "Account Type"]],
                    column_config = {
                        # "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="$%.2f CAD"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category", options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )
            with tab2:
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()
                st.subheader("Your Payments")
                st.session_state.outflow_df = st.session_state.outflow_df[
                    st.session_state.outflow_df["Account Type"] == "Credit"
                ]
                total_payments = st.session_state.outflow_df['Amount'].sum()
                st.metric("Total Payments", f"${total_payments:,.2f} CAD")
                edited_df = st.data_editor(
                    st.session_state.outflow_df[["Date", "Details", "Amount", "Category", "Account", "Account Type"]],
                    column_config = {
                        # "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="$%.2f CAD"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category", options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor_outflow"
                )
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == st.session_state.outflow_df.at[idx, "Category"]:
                            continue
                        details = row["Details"]
                        st.session_state.outflow_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)
                st.subheader("Expense Summary")
                category_totals = st.session_state.outflow_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values(by="Amount", ascending=False)
                st.dataframe(
                    category_totals, 
                    column_config={
                        "Amount": st.column_config.NumberColumn("Amount", format="$%.2f CAD")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                fig = px.pie(
                    category_totals, 
                    names="Category", 
                    values="Amount", 
                    title="Expense Distribution by Category"
                )
                st.plotly_chart(fig, use_container_width=True)


main()