from flask import Flask, request, send_file, render_template, send_from_directory, render_template_string, redirect, url_for
import os
import pandas as pd
import re
import pycountry
from postcode_matcher import PostcodeMatcher

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

for folder in [UPLOAD_FOLDER, PROCESSED_FOLDER]:
    os.makedirs(folder, exist_ok=True)
    
matcher = PostcodeMatcher()

class DataCleanse:
    
    def __init__(self, file_path):
        self.process_file(file_path)
        matcher = PostcodeMatcher()
        
    def process_file(self, file_path):
        print("--- Processing : " + file_path)
        file_data = pd.read_csv(file_path)
        file_data.columns = file_data.columns.str.strip()
        file_data = file_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        file_data.rename(columns=lambda x: x.capitalize() if not x[0].isupper() else x, inplace=True)
        self.process_id_col(file_data)
        self.process_phone(file_data)
        self.process_landline(file_data)
        self.process_postcode(file_data)
        self.process_email(file_data)                          
        self.process_address(file_data)
        self.process_phone(file_data)
        self.remove_parent_duplicates(file_data)
        self.convert_countries_to_iso(file_data)
        self.create_error_columns(file_data)
        file_data.fillna("", inplace=True)
        file_data.replace({"nan": "", pd.NaT: ""}, inplace=True)
        file_data.to_csv(os.path.join(PROCESSED_FOLDER, os.path.basename(file_path)), index=False, quoting=1)

    # Targeting Columns           
    

    def process_postcode(self, file_data):
        file_data['Postcode Errors'] = ""
        post_code_col_names = ["Post_Code", "postcode", "postal_code", "zip_code", "pc"]
        expected_postcode_col_idx = self.get_expected_col_idx(file_data, post_code_col_names)
        
        if expected_postcode_col_idx is None:
            print("PostCode Column Not Found")
            return file_data

        postcode_col_name = file_data.columns[expected_postcode_col_idx]

        # Validate and process postcodes using the existing methods
        self.process_all_rows(file_data, self.valid_postcode, expected_postcode_col_idx)
        self.convert_postcode_to_uppercase(file_data, expected_postcode_col_idx)

    def convert_postcode_to_uppercase(self, file_data, expected_col_idx):
        col_name = file_data.columns[expected_col_idx]
        file_data[col_name] = file_data[col_name].str.upper()
        print(f"Postcode values in column '{col_name}' converted to uppercase.")
        
    def convert_countries_to_iso(self, file_data):
        country_column = "Country"  
        if country_column in file_data.columns:  # Check if the 'Country' column exists
            for index, row in file_data.iterrows():
                country_name = row[country_column]
                if pd.notna(country_name):
                    country_iso = self.get_iso_code(country_name)
                    if country_iso:
                        file_data.at[index, country_column] = country_iso
                    else:
                        print(f"ISO code not found for country: {country_name}")
        else:
            print("Warning: 'Country' column not found in the dataset. Skipping conversion to ISO.")

        # Write the updated data back to the dataframe or file if needed       

    def get_iso_code(self, country_name):
        try:
            country = pycountry.countries.lookup(country_name)
            return country.alpha_3
        except LookupError:
            return None 
            
    def process_id_col(self, file_data):
        id_col_names = ["ID", "Usr_ID", "User_ID"]
        expected_col_idx = self.get_expected_col_idx(file_data, id_col_names)
        if expected_col_idx is None:
            print("ID Column Not Found")
            return file_data
        col_name = file_data.columns[expected_col_idx]
        
        # Remove letters from the ID column, keeping specified special characters
        file_data[col_name] = file_data[col_name].apply(lambda x: re.sub(r'[A-Za-z]', '', str(x)))
        
      
    def process_phone(self, file_data):
        phone_col_names = ["phone", "Phone", "Phone Number"]
        expected_col_idx = self.get_expected_col_idx(file_data, phone_col_names)
        if expected_col_idx is None:
            print("Phone Column Not Found")
            return
        col_name = file_data.columns[expected_col_idx]

        # Apply existing phone validation to all rows in the phone column
        self.process_all_rows(file_data, self.valid_phone, expected_col_idx)

        # Remove letters from the phone numbers, keeping specified special characters
        file_data[col_name] = file_data[col_name].apply(lambda x: re.sub(r'[A-Za-z]', '', str(x)))

        # Remove values within parentheses from the phone numbers
        file_data[col_name] = file_data[col_name].apply(self.remove_values_within_parentheses)
        
    def process_landline(self, file_data):
        phone_col_names = ["landline"]
        expected_col_idx = self.get_expected_col_idx(file_data, phone_col_names)
        if expected_col_idx is None:
            print("Landline Column Not Found")
            return
        col_name = file_data.columns[expected_col_idx]

        # Apply existing landline validation to all rows in the landline column
        self.process_all_rows(file_data, self.valid_landline, expected_col_idx)

        # Remove letters from the landline numbers, keeping specified special characters
        file_data[col_name] = file_data[col_name].apply(lambda x: re.sub(r'[A-Za-z]', '', str(x)))

        # Remove values within parentheses from the landline numbers
        file_data[col_name] = file_data[col_name].apply(self.remove_values_within_parentheses)


    def remove_values_within_parentheses(self, input_string):
        # Convert input to string, if it's not already
        input_string = str(input_string)
        pattern = r"\s*\([^)]*\)"
        return re.sub(pattern, "", input_string)

    def process_email(self, file_data):
        email_col_names = ["email", "email address"]
        expected_col_idx = self.get_expected_col_idx(file_data, email_col_names)
        if expected_col_idx is None:
            print("Email Column Not Found")
            return file_data
        self.process_all_rows(file_data, self.valid_email, expected_col_idx)
        # Preprocess the email column: replace spaces with commas only if no commas are present
        file_data[file_data.columns[expected_col_idx]] = file_data[file_data.columns[expected_col_idx]].apply(
            lambda email: str(email).replace(" ", ",") if "," not in str(email) else email
        )
        
        # Validate and fill error column for original email column
        email_errors_column_name = "Email Errors"
        file_data[email_errors_column_name] = ""
        for index, row in file_data.iterrows():
            email_value = str(row[file_data.columns[expected_col_idx]])
            if email_value.strip() and not self.valid_email(email_value.strip()):
                file_data.at[index, email_errors_column_name] = email_value.strip()
        
        # Check if "Emails (Additional)" column already exists
        if "Emails (Additional)" in file_data.columns:
            additional_emails_col_name = "Emails (Additional)"
            # Iterate over each row
            for index, row in file_data.iterrows():
                email_values = str(row[file_data.columns[expected_col_idx]]).split(",")  # Split email values at commas
                if len(email_values) > 1:
                    # Move additional emails to "Emails (Additional)" column
                    file_data.at[index, additional_emails_col_name] = ", ".join(email_values[1:]).strip()
                    # Update the original column with the first email
                    file_data.at[index, file_data.columns[expected_col_idx]] = email_values[0].strip()

            

        else:
            # Create "Additional Emails" column
            additional_emails_col_name = "Additional Emails"
            # Initialize the additional email column
            file_data[additional_emails_col_name] = ""
            # Move additional emails to "Additional Emails" column
            for index, row in file_data.iterrows():
                email_values = str(row[file_data.columns[expected_col_idx]]).split(",")  # Split email values at commas
                if len(email_values) > 1:
                    # Move additional emails to "Additional Emails" column
                    file_data.at[index, additional_emails_col_name] = ", ".join(email_values[1:]).strip()
                    # Update the original column with the first email
                    file_data.at[index, file_data.columns[expected_col_idx]] = email_values[0].strip()

            # Create error column for "Additional Emails"
            additional_emails_errors_column_name = "Additional Emails Errors"
            file_data[additional_emails_errors_column_name] = ""
            # Iterate over each row in "Additional Emails" column
            for index, row in file_data.iterrows():
                email_values = str(row[additional_emails_col_name]).split(",")  # Split email values at commas
                for email in email_values:
                    email = email.strip()  # Remove leading/trailing whitespaces
                    if email and not self.valid_email(email):
                        # Flag invalid emails in the "Additional Emails Errors" column
                        file_data.at[index, additional_emails_errors_column_name] += email + ", "
            # Remove trailing comma from error column
            file_data[additional_emails_errors_column_name] = file_data[additional_emails_errors_column_name].str.rstrip(", ")

        

        return file_data

        
    def process_address(self, file_data):
        address_col_names = ["street address 1", "street address 2", "address", "address 2"]
        expected_col_idx = self.get_expected_col_idx(file_data, address_col_names)

        # Check if any of the address columns exist
        if expected_col_idx is None:
            print("Address Columns Not Found")
            return

        # Check if both "Street Address 1" and "Street Address 2" columns exist
        if "Street Address 1" in file_data.columns and "Street Address 2" in file_data.columns:
            street_address_1_col = "Street Address 1"
            street_address_2_col = "Street Address 2"
            # Check if Street Address 1 is null for all rows
            if file_data[street_address_1_col].isnull().all():
                # If Street Address 1 is null for all rows, set it to Street Address 2
                file_data[street_address_1_col] = file_data[street_address_2_col]
                # Remove duplicates from Street Address 2
                file_data[street_address_2_col] = ""
            else:
                # Move values from Street Address 2 to Street Address 1 where Street Address 1 is null
                street_address_1_null_mask = file_data[street_address_1_col].isnull()
                file_data.loc[street_address_1_null_mask, street_address_1_col] = file_data.loc[street_address_1_null_mask, street_address_2_col]
                # Remove duplicates from Street Address 2
                file_data[street_address_2_col] = file_data[street_address_2_col].where(file_data[street_address_1_col] != file_data[street_address_2_col], "")
        else:
            # If either column is missing, print a message
            if "Street Address 1" not in file_data.columns:
                print("Street Address 1 Column Not Found")
            if "Street Address 2" not in file_data.columns:
                print("Street Address 2 Column Not Found")

        return file_data

            
    def remove_parent_duplicates(self, file_data):
        special_col_names = ["Name", "Site", "Customer"]
        expected_col_idx = self.get_expected_col_idx(file_data, special_col_names)
        
        # Check if "Parent" column exists in the dataset
        if "Parent" in file_data.columns:
            # Strip leading and trailing whitespaces from the "Parent" column
            file_data["Parent"] = file_data["Parent"].str.strip()
            
            # Iterate through each column in special_col_names
            for col_name in special_col_names:
                # Check if the column exists in the dataset
                if col_name in file_data.columns:
                    # Identify rows where "Parent" values match values in the current column
                    duplicates_mask = file_data["Parent"] == file_data[col_name]
                    
                    if duplicates_mask.any():
                        # Set duplicate "Parent" values to an empty string
                        file_data.loc[duplicates_mask, "Parent"] = ""
                        print(f"Duplicates between 'Parent' and '{col_name}' columns removed.")
                    else:
                        print(f"No duplicates found between 'Parent' and '{col_name}' columns.")
                else:
                    print(f"Error: '{col_name}' column not found in the dataset.")
        else:
            print("Error: 'Parent' column not found in the dataset.")
        
        return file_data
        
    def create_error_columns(self, file_data):
        # Define the columns to create error columns for
        columns_to_check = ["postcode", "phone", "email", "landline", "additional emails", "emails (additional)"]

        # Initialize variables for the additional emails column and its errors column
        additional_emails_column_name = "Additional Emails"
        additional_emails_errors_column_name = "Additional Emails Errors"

        # Check if "Emails (Additional)" exists in the dataset
        if "Emails (Additional)" in file_data.columns:
            additional_emails_column_name = "Emails (Additional)"
            additional_emails_errors_column_name = "Emails (Additional) Errors"

            # Create the error column for "Emails (Additional)"
            file_data[additional_emails_errors_column_name] = ""

            # Iterate over each row to validate emails in "Emails (Additional)" column and fill error column
            for index, row in file_data.iterrows():
                email_values = str(row[additional_emails_column_name]).split(",")  # Split email values at commas
                for email in email_values:
                    email = email.strip()  # Remove leading/trailing whitespaces
                    if email and not self.valid_email(email):
                        file_data.at[index, additional_emails_errors_column_name] += email + ", "

            # Remove trailing comma from error column
            file_data[additional_emails_errors_column_name] = file_data[additional_emails_errors_column_name].str.rstrip(", ")

        else:
            # If "Emails (Additional)" column does not exist, set the error column name to None
            additional_emails_errors_column_name = None

        # Iterate over each column to create error columns
        for column_name in file_data.columns:
            for check_column in columns_to_check:
                # Replace spaces with underscores in check_column
                check_column_attr = check_column.lower().replace(" ", "_")
                
                if check_column_attr in column_name.lower():
                    # Determine the error column name based on the existence of "Emails (Additional)"
                    error_column_name = additional_emails_errors_column_name if check_column_attr == "emails_(additional)" else f"{check_column.capitalize()} Errors"
                    valid_func = getattr(self, f"valid_{check_column_attr}")
                    
                    # Fill the error column with invalid values from the corresponding column
                    invalid_values_mask = ~file_data.apply(lambda row: valid_func(str(row[column_name])), axis=1)
                    file_data.loc[invalid_values_mask, error_column_name] = file_data.loc[invalid_values_mask, column_name]

        # Check for variations of the email column name and create an "Email Errors" column to mark down email errors
        email_column_variations = ["email", "Email", "Email Address"]
        for variation in email_column_variations:
            if variation in file_data.columns:
                file_data["Email Errors"] = ""
                for index, row in file_data.iterrows():
                    email_value = str(row[variation])
                    # Check if the email contains multiple "@" symbols or multiple email addresses
                    if email_value.count("@") > 1 or len(email_value.split()) > 1:
                        # Mark down the email address as an error in the "Email Errors" column
                        file_data.at[index, "Email Errors"] = email_value
                    elif not self.valid_email(email_value):  # Check if email is invalid
                        file_data.at[index, "Email Errors"] = email_value

        return file_data

    def get_expected_col_idx(self, file_data, column_names):
        for idx, column in enumerate(file_data.columns):
            if column.lower() in column_names:
                return idx
        return None      

    def process_all_rows(self, file_data, valid, expected_col_idx):
        for row_idx, row in file_data.iterrows():
            for col_idx, column in enumerate(file_data.columns):
                if valid(str(row[column])) and col_idx != expected_col_idx:
                    self.swap_col_data(file_data, row_idx, col_idx, expected_col_idx)

    #validation/regex

    def valid_postcode(self, post_code):
        uk_post_code_pattern = r"^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))\s?[0-9][A-Za-z]{2})"
        american_pc_pattern = r"^\d{5}(-\d{4})?$"

        return bool(re.match(uk_post_code_pattern, post_code))
        
    def validate_pcl(self, file_data):
        post_code_col_names = ["postcode", "postal_code", "zip_code", "pc"]
        expected_col_idx = self.get_expected_col_idx(file_data, post_code_col_names)
        if expected_col_idx is None:
            print("PostCode Column Not Found")
            return file_data

        col_name = file_data.columns[expected_col_idx]

        # Iterate through each row to match postcode to ISO code and handle errors
        for index, row in file_data.iterrows():
            postcode = row[col_name]
            iso_code = matcher.match_postcode_to_iso(postcode)
            if iso_code is None:
                # If no matching ISO code is found, set the error value
                file_data.at[index, 'Postcode Errors'] = f'Postcode {postcode} does not match any country ISO code pattern.'
            else:
                # If a matching ISO code is found, check if the postcode matches the pattern for the ISO code
                if not matcher.validate_postcode_for_country(postcode, iso_code):
                    # If the postcode does not match the pattern, flag it in the error column
                    file_data.at[index, 'Postcode Errors'] = f'Postcode {postcode} does not match the pattern for country {iso_code}.'

        return file_data
          
    def valid_phone(self, phone):
        if self.valid_phone_for_country(phone, "United Kingdom"):
            return True
        elif self.valid_phone_for_country(phone, "United States"):
            return True
        elif self.valid_phone_for_country(phone, "Ireland"):
            return True
        # Add more conditions for other countries...
        else:
            return False
            
    def valid_phone_for_country(self, phone, country):
        if country == "United Kingdom":
            uk_phone_pattern = r"^\d{3}\s\d{8,}$"
            return bool(re.match(uk_phone_pattern, phone))
        elif country == "United States":
            usa_phone_pattern = r"^\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"
            return bool(re.match(usa_phone_pattern, phone))
        elif country == "Ireland":
            ireland_phone_pattern = r"^\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"  # Example pattern for Ireland, adjust as needed
            return bool(re.match(ireland_phone_pattern, phone))
        # Add more conditions for other countries...
        else:
            return False
    def valid_landline(self, phone):
        uk_phone_pattern = r"^(\d{2}\s\d{5}\s\d{5})$"
        return bool(re.match(uk_phone_pattern, phone))
    
    def valid_email(self, email):
        email_pattern = email_pattern = r'\S+@\S+\.\S+'
        return bool(re.match(email_pattern, email))
        
    def valid_additional(self, email):
        add_email = r"[\w\.-]+@[\w\.-]+(?:,\s*[\w\.-]+@[\w\.-]+)*"
        return bool(re.match(add_email, email))
           
    #validation/regex

    def swap_col_data(self, file_data, row_idx, col_idx_src, col_idx_des):
        src_col_data = file_data.iloc[row_idx, col_idx_src]
        des_col_data = file_data.iloc[row_idx, col_idx_des]
        file_data.iloc[row_idx, col_idx_des] = src_col_data
        file_data.iloc[row_idx, col_idx_src] = des_col_data

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/preview/<filename>')
def preview(filename):
    processed_filename = os.path.join(PROCESSED_FOLDER, filename)
    # Read the processed file and return its contents
    with open(processed_filename, 'r') as processed_file:
        processed_data = processed_file.read()
    return render_template('preview.html', processed_data=processed_data)

@app.route('/process_file', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        data_cleanse = DataCleanse(filename)
        processed_filename = os.path.join(PROCESSED_FOLDER, os.path.basename(filename))
        # Read the processed file and return its contents
        with open(processed_filename, 'r') as processed_file:
            processed_data = processed_file.read()
        return processed_data
    return 'Error processing file'
    

@app.route('/process_and_preview', methods=['POST'])
def process_and_preview():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        data_cleanse = DataCleanse(filename)
        
        # Process the file and save the processed data to a temporary file
        processed_filename = os.path.join(PROCESSED_FOLDER, os.path.basename(filename))
        with open(processed_filename, 'r') as processed_file:
            processed_data = processed_file.read()
        
        # Render the preview page with the processed data
        return render_template('preview.html', processed_data=processed_data)
    return 'Error processing file'

@app.route('/login', methods=['POST'])
def login_post():
    password = request.form.get('password')

    # Replace this condition with your actual password validation logic
    if password == "1234":
        # Redirect to some other page on successful login
        return redirect(url_for('index'))
    else:
        # Render the login page with an error message
        return render_template('login.html', message="Password incorrect please try again later")

@app.route('/download_processed_file/<filename>')
def download_processed_file(filename):
    return send_from_directory(PROCESSED_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
