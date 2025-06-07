from app import create_app, db
from app.models import User

app = create_app()
db.create_all()    
if __name__ == "__main__":
   
    app.run(host="0.0.0.0", port=5000)

