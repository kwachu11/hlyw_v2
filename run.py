from app import create_app

app = create_app()
app.config.from_object('config.Config')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  # Możesz zmienić port na odpowiedni