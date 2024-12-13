from app import app
import os

if __name__ == '__main__':
    if os.getenv('ADHOC_SSL', True):
        app.run(debug=os.getenv('DEBUG', False), port=os.getenv('PORT', 8443), host=os.getenv('HOST', '0.0.0.0'), ssl_context='adhoc')
    else:
        app.run(debug=os.getenv('DEBUG', False), port=os.getenv('PORT', 8000), host=os.getenv('HOST', '0.0.0.0'))
