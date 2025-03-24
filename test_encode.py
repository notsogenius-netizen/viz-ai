import unittest
from urllib.parse import urlparse, quote_plus

def encode_db_password(connection_string):
    """Extracts and encodes the password part of a PostgreSQL connection string."""
    parsed_url = urlparse(connection_string)
    raw_password = parsed_url.password or ""  # Ensure empty string instead of None
    encoded_password = quote_plus(raw_password)

    # Construct new connection string with encoded password
    new_connection_string = f"{parsed_url.scheme}://{parsed_url.username}:{encoded_password}@{parsed_url.hostname}{':' + str(parsed_url.port) if parsed_url.port else ''}{parsed_url.path}?{parsed_url.query}"
    
    return encoded_password, new_connection_string


class TestPasswordEncoding(unittest.TestCase):
    def test_password_with_special_chars(self):
        connection_string = "postgresql://user:pass@word@host:5432/dbname?sslmode=require"
        expected_encoded_password = "pass%40word"
        encoded_password, new_conn_string = encode_db_password(connection_string)
        
        self.assertEqual(encoded_password, expected_encoded_password)
        self.assertIn("pass%40word@", new_conn_string)

    def test_password_without_special_chars(self):
        connection_string = "postgresql://user:password@host:5432/dbname?sslmode=require"
        expected_encoded_password = "password"
        encoded_password, new_conn_string = encode_db_password(connection_string)
        
        self.assertEqual(encoded_password, expected_encoded_password)
        self.assertIn("password@", new_conn_string)

    def test_password_with_multiple_special_chars(self):
        connection_string = "postgresql://user:pa$$@word!@host:5432/dbname?sslmode=require"
        expected_encoded_password = "pa%24%24%40word%21"
        encoded_password, new_conn_string = encode_db_password(connection_string)
        
        self.assertEqual(encoded_password, expected_encoded_password)
        self.assertIn("pa%24%24%40word%21@", new_conn_string)

    def test_missing_password(self):
        connection_string = "postgresql://user:@host:5432/dbname?sslmode=require"
        expected_encoded_password = ""
        encoded_password, new_conn_string = encode_db_password(connection_string)
        
        self.assertEqual(encoded_password, expected_encoded_password)
        self.assertIn(":@host", new_conn_string)

if __name__ == "__main__":
    unittest.main()
