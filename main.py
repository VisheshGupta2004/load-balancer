"""
main.py
-------
Entry point for the Load Balancer Flask application.

Run locally:
    python main.py

Run with gunicorn (production):
    gunicorn main:app --workers 2
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n" + "═"*50)
    print("  Rendezvous Load Balancer  —  v1.0.0")
    print("  Algorithm : Rendezvous Hashing (HRW)")
    print("  Server    : http://127.0.0.1:5000")
    print("═"*50 + "\n")
    app.run(debug=True, port=5000)
