import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

def clean_numeric_column(df, column_name):
    """Clean numeric columns from CSV"""
    if column_name in df.columns:
        # Remove currency symbols and commas
        df[column_name] = df[column_name].astype(str).str.replace('[$,₹€£,]', '', regex=True)
        # Convert to numeric, coerce errors
        df[column_name] = pd.to_numeric(df[column_name], errors='coerce')
    return df

def filter_by_category(df, category_keywords, text_column='name'):
    """Filter dataframe by category keywords"""
    if text_column not in df.columns:
        return df
    
    mask = pd.Series(False, index=df.index)
    for keyword in category_keywords:
        mask = mask | df[text_column].str.contains(keyword, case=False, na=False)
    
    return df[mask]