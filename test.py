import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import json
import os

file = "cibc.csv"
file2 = "activity.csv"
file3 = "cibc (1).csv"
# Define column names (header)
column_names = ['Date', 'Details', 'Amount Owed', 'Amount Paid', 'Card']
column_names2 = ['Date', 'Details', 'Amount Owed', 'Amount Paid']

# Load CSV without header
df = pd.read_csv(file, header=None, names=column_names)
df['Date'] = pd.to_datetime(df['Date'])
mask = df['Amount Owed'].isnull()
df.loc[mask, 'Amount Owed'] = df['Amount Paid']*-1

df_amex = pd.read_csv(file2)
df_amex["Date"] = pd.to_datetime(df_amex["Date"].str.strip(), format="%d %b %Y")

df_cibc = pd.read_csv(file3, header=None, names=column_names2)
df_cibc['Date'] = pd.to_datetime(df_cibc['Date'])
mask = df_cibc['Amount Owed'].isnull()
df_cibc.loc[mask, 'Amount Owed'] = df_cibc['Amount Paid']*-1

df_cibc_credit = pd.DataFrame({
    'Date': df['Date'],
    'Details': df['Details'].str.strip(),
    'Category': 'Uncategorized',
    'Amount': df['Amount Owed'],
    'Account': 'CIBC',
    'Account Type': 'Credit'
})

df_amex_credit = pd.DataFrame({
    'Date': df_amex['Date'],
    'Details': df_amex['Description'].str.strip(),
    'Category': 'Uncategorized',
    'Amount': df_amex['Amount'],
    'Account': 'Amex',
    'Account Type': 'Credit'
})

df_cibc_debit = pd.DataFrame({
    'Date': df_cibc['Date'],
    'Details': df_cibc['Details'].str.strip(),
    'Category': 'Uncategorized',
    'Amount': df_cibc['Amount Owed'],
    'Account': 'CIBC',
    'Account Type': 'Debit'
})

result = pd.concat([df_cibc_credit, df_amex_credit, df_cibc_debit], ignore_index=True)
result = result.sort_values(by='Date', ascending=False)

result.to_csv("combined_transactions.csv", index=False)