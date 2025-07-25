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

def load_transactions(files):
    """Load and combine transactions from multiple CSV files"""
    all_dataframes = []
    
    for file in files:
        try:
            df = pd.read_csv(file)
            # Add source file column to track which file each transaction came from
            df['Source_File'] = file.name
            # clean up column names
            df.columns = [col.strip() if col != 'Source_File' else col for col in df.columns]
            # remove commas from monetary values and convert to float
            df["Amount"] = df["Amount"].str.replace(",","").astype(float)
            # convert date strings to datetime objects
            df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
            all_dataframes.append(df)
            st.success(f"✅ Successfully loaded {file.name} ({len(df)} transactions)")
        except Exception as e:
            st.error(f"❌ Error loading {file.name}: {str(e)}")
            continue
    
    if not all_dataframes:
        return None
    
    # Combine all dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    # Sort by date for better organization
    combined_df = combined_df.sort_values('Date').reset_index(drop=True)
    
    st.info(f"📊 Combined total: {len(combined_df)} transactions from {len(files)} files")
    
    return categorize_transactions(combined_df)
    
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
    
    # Modified file uploader to accept multiple files
    uploaded_files = st.file_uploader(
        "Upload your transaction CSV files", 
        type=["csv"], 
        accept_multiple_files=True,
        help="You can select multiple CSV files to combine all transactions"
    )

    if uploaded_files:
        df = load_transactions(uploaded_files)
        if df is not None:
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()

            st.session_state.debits_df = debits_df.copy()

            # Display file summary
            with st.expander("📁 File Summary", expanded=False):
                file_summary = df.groupby('Source_File').agg({
                    'Amount': ['count', 'sum'],
                    'Date': ['min', 'max']
                }).round(2)
                file_summary.columns = ['Transaction Count', 'Total Amount', 'Earliest Date', 'Latest Date']
                st.dataframe(file_summary, use_container_width=True)

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])
            
            with tab1:
                col1, col2 = st.columns([1, 1])
                with col1:
                    new_category = st.text_input("New Category Name")
                with col2:
                    add_button = st.button("Add Category")
                
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()
                
                st.subheader("Your Expenses")
                
                # Add filter options
                col1, col2, col3 = st.columns(3)
                with col1:
                    # File filter
                    available_files = sorted(st.session_state.debits_df['Source_File'].unique())
                    selected_files = st.multiselect(
                        "Filter by files:", 
                        available_files, 
                        default=available_files,
                        help="Select which files to include in the view"
                    )
                
                with col2:
                    # Category filter
                    available_categories = sorted(st.session_state.debits_df['Category'].unique())
                    selected_categories = st.multiselect(
                        "Filter by categories:", 
                        available_categories, 
                        default=available_categories
                    )
                
                with col3:
                    # Date range filter
                    min_date = st.session_state.debits_df['Date'].min().date()
                    max_date = st.session_state.debits_df['Date'].max().date()
                    date_range = st.date_input(
                        "Date range:",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date
                    )
                
                # Apply filters
                filtered_debits = st.session_state.debits_df[
                    (st.session_state.debits_df['Source_File'].isin(selected_files)) &
                    (st.session_state.debits_df['Category'].isin(selected_categories))
                ]
                
                if len(date_range) == 2:
                    filtered_debits = filtered_debits[
                        (filtered_debits['Date'].dt.date >= date_range[0]) &
                        (filtered_debits['Date'].dt.date <= date_range[1])
                    ]
                
                edited_df = st.data_editor(
                    filtered_debits[["Date", "Details", "Amount", "Category", "Source_File"]],
                    column_config = {
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="$%.2f AED"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category", options=list(st.session_state.categories.keys())
                        ),
                        "Source_File": st.column_config.TextColumn("Source File", disabled=True)
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )
                
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    changes_made = 0
                    
                    # Use a more robust approach by matching on unique row characteristics
                    for display_idx, edited_row in edited_df.iterrows():
                        try:
                            # Find the matching row in the original dataframe using multiple criteria
                            matching_rows = st.session_state.debits_df[
                                (st.session_state.debits_df['Date'] == edited_row['Date']) &
                                (st.session_state.debits_df['Details'] == edited_row['Details']) &
                                (st.session_state.debits_df['Amount'] == edited_row['Amount']) &
                                (st.session_state.debits_df['Source_File'] == edited_row['Source_File'])
                            ]
                            
                            if len(matching_rows) == 0:
                                st.warning(f"Could not find matching row for: {edited_row['Details']}")
                                continue
                            elif len(matching_rows) > 1:
                                # If multiple matches, take the first one
                                original_idx = matching_rows.index[0]
                            else:
                                original_idx = matching_rows.index[0]
                            
                            new_category = edited_row["Category"]
                            
                            # Check if category actually changed
                            if new_category == st.session_state.debits_df.at[original_idx, "Category"]:
                                continue
                            
                            # Update the category in the original dataframe
                            details = edited_row["Details"]
                            st.session_state.debits_df.at[original_idx, "Category"] = new_category
                            add_keyword_to_category(new_category, details)
                            changes_made += 1
                            
                        except Exception as e:
                            st.error(f"Error updating row {display_idx}: {str(e)}")
                            continue
                    
                    if changes_made > 0:
                        st.success(f"✅ {changes_made} changes applied successfully!")
                        st.rerun()
                    else:
                        st.info("No changes detected.")
                
                st.subheader("Expense Summary")
                
                # Summary for filtered data
                category_totals = filtered_debits.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values(by="Amount", ascending=False)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(
                        category_totals, 
                        column_config={
                            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f AED")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                
                with col2:
                    if not category_totals.empty:
                        fig = px.pie(
                            category_totals, 
                            names="Category", 
                            values="Amount", 
                            title="Expense Distribution by Category"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # Additional summary by file
                st.subheader("Summary by File")
                file_summary = filtered_debits.groupby("Source_File")["Amount"].sum().reset_index()
                file_summary = file_summary.sort_values(by="Amount", ascending=False)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.dataframe(
                        file_summary,
                        column_config={
                            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f AED")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                
                with col2:
                    if not file_summary.empty:
                        fig_files = px.bar(
                            file_summary,
                            x="Source_File",
                            y="Amount",
                            title="Expenses by File"
                        )
                        fig_files.update_layout(xaxis_tickangle=45)
                        st.plotly_chart(fig_files, use_container_width=True)
            
            with tab2:
                st.subheader("Your Payments")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"${total_payments:,.2f} AED")
                
                # Show payments with source file information
                st.dataframe(
                    credits_df[["Date", "Details", "Amount", "Source_File"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="$%.2f AED"),
                        "Source_File": st.column_config.TextColumn("Source File")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Summary by file for credits
                if not credits_df.empty:
                    st.subheader("Payments by File")
                    credits_by_file = credits_df.groupby("Source_File")["Amount"].sum().reset_index()
                    st.dataframe(
                        credits_by_file,
                        column_config={
                            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f AED")
                        },
                        use_container_width=True,
                        hide_index=True
                    )

if __name__ == "__main__":
    main()