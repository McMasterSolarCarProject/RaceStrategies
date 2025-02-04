import sqlite3

#TO TEST THE DATABASE
def create_test_data():

    conn = sqlite3.connect('source.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        )
    ''')

    cursor.executemany(
        "INSERT INTO users (name, age) VALUES (?, ?)",
        [('Alice', 30), ('Bob', 25), ('Charlie', 35)]
    )

    conn.commit()
    conn.close()
    
    
    print("test data created")

def process_data(data):

    #CALCULATE INFORMATION

    processed_data = [(row[0], row[1], row[2] + 10) for row in data]
    return processed_data

def run_test():
    
    print("Script is running...")

    create_test_data()

    source_conn = sqlite3.connect('source.db')
    source_cursor = source_conn.cursor()


    source_cursor.execute("SELECT id, name, age FROM users")
    source_data = source_cursor.fetchall()

    processed_data = process_data(source_data)

    destination_conn = sqlite3.connect('destination.db')
    destination_cursor = destination_conn.cursor()

    destination_cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            adjusted_age INTEGER
        ) 
    ''')
    destination_conn.commit()

    destination_cursor.executemany(
        "INSERT OR REPLACE INTO processed_users (id, name, adjusted_age) VALUES (?, ?, ?)",
        processed_data
    )
    destination_conn.commit()

    source_conn.close()
    destination_conn.close()

    print("Done")
