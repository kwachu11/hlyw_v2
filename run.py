from app import create_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

app = create_app()
app.config.from_object('config.Config')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  # Możesz zmienić port na odpowiedni