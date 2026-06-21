from app import create_app
app = create_app()
print("App OK:", app.name)
print("Routes:", len(app.url_map._rules))