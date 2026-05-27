import pandas as pd
import requests

# Load Excel file
input_file = r"FT Data.xlsx"
output_file = r"corrected_output.xlsx"

# Read Excel
df = pd.read_excel(input_file)

# Wrong and correct URL parts
wrong_part = "https://storage.googleapis.com/joshtalks-data-collection/hq_data/hi/"
correct_part = "https://storage.googleapis.com/upload_goai/"

# URL columns
url_columns = ["rec_url_gcp", "transcription_url_gcp", "metadata_url_gcp"]   # replace with actual column names

# Function to validate URL
def validate_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False

# Fix + validate
for col in url_columns:

    # Replace wrong URL base
    df[col] = df[col].astype(str).str.replace(
        wrong_part,
        correct_part,
        regex=False
    )

    # Validation column
    validation_col = f"{col}_valid"

    # Check URLs
    df[validation_col] = df[col].apply(validate_url)

# Save corrected file
df.to_excel(output_file, index=False)

print("URLs corrected and validated.")
print("Saved file:", output_file)