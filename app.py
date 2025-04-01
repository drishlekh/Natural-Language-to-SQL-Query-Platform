from flask import Flask, render_template, request
import mysql.connector
import groq
import os
from dotenv import load_dotenv

# Loading environment variables
try:
    load_dotenv(encoding='utf-8')
    if not os.getenv('GROQ_API_KEY'):
        print("Warning: GROQ_API_KEY not found in .env file")
except Exception as e:
    print(f"Error loading .env file: {e}")
    print("Please ensure .env file exists and is properly formatted")

app = Flask(__name__)

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE'),
    'buffered': True
}

# Initialize Groq client
groq_client = groq.Client(api_key=os.getenv('GROQ_API_KEY'))

def get_db_connection():
    """Create and return a database connection."""
    return mysql.connector.connect(**db_config)

def test_db_connection():
    """Test the database connection."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT 1")
        cursor.fetchall()
        print("Database connection successful!")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def natural_to_sql(natural_query):
    """
    Convert a natural language query to an SQL query using Groq's API.
    """
    prompt = f"""
    Convert the following natural language query to a MySQL query.
    The query should be for a restaurants table with columns:
    id, name, special_dish, rating, location, cuisine, contact_number, opening_hours, created_at

    Natural language query: {natural_query}

    Return only the SQL query without any explanation or formatting.
    """

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",  
            temperature=0.5,
        )
        
        sql_query = response.choices[0].message.content.strip()

        #
        if sql_query.startswith("```sql") and sql_query.endswith("```"):
            sql_query = sql_query[6:-3].strip()  

        
        sql_query = sql_query.replace('\_', '_')  
        sql_query = sql_query.replace('\*', '*') 
        sql_query = sql_query.replace('\\', '')  

        return sql_query
    except Exception as e:
        print(f"Error in natural_to_sql: {e}")
        raise Exception("Failed to convert natural language to SQL query")

def execute_query(sql_query):
    """Execute the SQL query and return the results."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        print(f"Executing query: {sql_query}") 
        cursor.execute(sql_query)
        results = cursor.fetchall()
        return results if results else []
    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
        raise Exception(f"Database error: {str(e)}")
    except Exception as e:
        print(f"General error: {e}")
        raise Exception(f"Error: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main route."""
    results = []
    natural_query = ''
    sql_query = ''
    error = None

    if request.method == 'POST':
        natural_query = request.form['natural_query'].strip()
        if not natural_query:
            error = "Please enter a query"
        else:
            try:
                sql_query = natural_to_sql(natural_query)
                if sql_query:
                    results = execute_query(sql_query)
                    if not results:
                        error = "No results found for your query"
                else:
                    error = "Failed to generate SQL query"
            except Exception as e:
                error = str(e)
                results = []

    return render_template('index.html',
                         results=results,
                         natural_query=natural_query,
                         sql_query=sql_query,
                         error=error)

if __name__ == '__main__':
    if test_db_connection():
        app.run(debug=True)
    else:
        print("Please check your database configuration.")