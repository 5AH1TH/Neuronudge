import os
from Neuronudge import create_app

# Create the Flask app using your factory pattern
app = create_app()

if __name__ == "__main__":
    # Print URL for local dev convenience
    print("App running at: http://127.0.0.1:5000/")
    # Bind to 0.0.0.0 for Azure compatibility, port from environment
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
