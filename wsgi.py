from app import app
import os

if __name__ == '__main__':
    app.run(debug=os.getenv('DEBUG', False), port=os.getenv('PORT', 443), host=os.getenv('HOST', '0.0.0.0'), ssl_context='adhoc')
