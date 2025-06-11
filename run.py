from app import app

if __name__ == "__main__":
    print("🚀 Starting Enhanced Photo Tampering Detection Application...")
    print("📍 Server will be available at: http://localhost:5001")
    print("🔍 Features: ELA Analysis, HEIC Support, Drag & Drop Interface")
    print("⚡ Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

