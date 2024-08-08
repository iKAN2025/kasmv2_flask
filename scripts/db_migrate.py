#!/usr/bin/env python3

""" db_init.py
Generates the database schema for all db models
- Initializes Users, Sections, and UserSections tables.
- Imports data from the old database to the new database.

Usage: Run from the terminal as such:

Goto the scripts directory:
> cd scripts; ./db_migrate.py

Or run from the root of the project:
> scripts/db_migrate.py

General Process outline:
0. Warning to the user.
1. Old data extraction.  An API has been created in the old project ...
  - Extract Data: retrieves data from the specified tables in the old database.
  - Transform Data: the API to JSON format understood by the new project.
2. New schema.  The schema is created in "this" new database.
3. Load Data: The bulk load API in "this" project inserts the data using required business logic.

"""
import shutil
import sys
import os
import requests

# Add the directory containing main.py to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Import application object
from main import app, db, initUsers

# Locations and credentials 
AUTH_URL = "https://flask2.nighthawkcodingsociety.com/api/authenticate"
OLD_DATA_URL = "https://flask2.nighthawkcodingsociety.com/api/user"
UID = app.config['DEFAULT_USER'] 
PASSWORD = app.config['DEFAULT_PASSWORD']

# Backup the old database
def backup_database(db_uri, backup_uri):
    """Backup the current database."""
    if backup_uri:
        db_path = db_uri.replace('sqlite:///', 'instance/')
        backup_path = backup_uri.replace('sqlite:///', 'instance/')
        shutil.copyfile(db_path, backup_path)
        print(f"Database backed up to {backup_path}")
    else:
        print("Backup not supported for production database.")
        
# Old data access        
def authenticate(uid, password):
    '''Authenticate and return the token'''
    auth_data = {
        "uid": uid,
        "password": password
    }
    headers = {
        "Content-Type": "application/json",
        "X-Origin": "client"
    }
    try:
        response = requests.post(AUTH_URL, json=auth_data, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.cookies, None
    except requests.RequestException as e:
        return None, {'message': 'Failed to authenticate', 'code': response.status_code, 'error': str(e)}

# Old data JSON extraction
def extract_old_data(cookies):
    '''Extract old data using the authentication cookies'''
    headers = {
        "Content-Type": "application/json",
        "X-Origin": "client"
    }
    try:
        response = requests.get(OLD_DATA_URL, headers=headers, cookies=cookies)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json(), None
    except requests.RequestException as e:
        return None, {'message': 'Failed to extract old data', 'code': response.status_code, 'error': str(e)}

# Main extraction and loading process
def main():
    
    # Step 0: Warning to the user and backup table
    with app.app_context():
        try:
            # Step 3: Build New schema
            # Check if the database has any tables
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if tables:
                print("Warning, you are about to lose all data in the database!")
                print("Do you want to continue? (y/n)")
                response = input()
                if response.lower() != 'y':
                    print("Exiting without making changes.")
                    sys.exit(0)
                    
            # Backup the old database
            backup_database(app.config['SQLALCHEMY_DATABASE_URI'], app.config['SQLALCHEMY_BACKUP_URI'])
            
        except Exception as e:
            print(f"An error occurred: {e}")
            sys.exit(1)
        
    # Step 1: Authenticate to Old database
    cookies, error = authenticate(UID, PASSWORD)
    if error:
        print(error)
        sys.exit(1)
    
    # Step 2: Extract Old data 
    old_data, error = extract_old_data(cookies)
    if error:
        print(error)
        sys.exit(1)
    
    print("Old data extracted successfully.")
    
    # Step 3: Build New schema and load data 
    with app.app_context():
        try:
            # Drop all the tables defined in the project
            db.drop_all()
            print("All tables dropped.")
            
            # Create all tables
            db.create_all()
            print("All tables created.")
            
            # Add default test data 
            initUsers() # test data
            
            # Load data into the new database using Flask's test client
            with app.test_client() as client:
                post_response = client.post('/api/users', json=old_data)
                if post_response.status_code == 200:
                    print("Data loaded into the new database successfully.")
                else:
                    print(f"Failed to load data into the new database. Status code: {post_response.status_code}")
                    sys.exit(1)
            
        except Exception as e:
            print(f"An error occurred: {e}")
            sys.exit(1)
    
    # Log success 
    print("Database initialized!")
 
if __name__ == "__main__":
    main()