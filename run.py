from app import create_app, db
import sys

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        print("🟢 Running db.create_all() in app context")
        print("🚀 Starting Enhanced Photo Tampering Detection Application...")
        print("📍 Server will be available at: http://localhost:5001")
        print("🔍 Features: ELA Analysis, HEIC Support, Drag & Drop Interface")
        print("⚡ Press Ctrl+C to stop the server")
        print("-" * 60)
        db.create_all()
    try:
        #app.run(debug=True, host="0.0.0.0", port=5001)
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

@app.errorhandler(500)
def internal_error(error):
    return "Something went wrong: " + str(error), 500

for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint}: {rule.rule}")
