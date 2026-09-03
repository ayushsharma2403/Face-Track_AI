from app import app

if __name__ == '__main__':
    # Skip face detection initialization
    print("Starting Flask server on http://127.0.0.1:5000")
    print("Note: Face recognition features are disabled")
    app.run(debug=True, host='0.0.0.0', port=5000)
