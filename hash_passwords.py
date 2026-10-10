# Jednorazowa migracja: hasła zapisane dawniej jako zwykły tekst zamieniamy na hashe.
# Uruchamiać ręcznie (python hash_passwords.py), nie przy starcie aplikacji - hashowanie
# jest celowo wolne i przy wielu kontach przekracza timeout workerów gunicorna.
# Konta, które już mają hash, są pomijane, więc skrypt można bezpiecznie puścić ponownie.
from app import create_app, hash_password, is_password_hash

app = create_app()

with app.app_context():
    db = app.extensions['sqlalchemy']
    User = next(m.class_ for m in db.Model.registry.mappers if m.class_.__name__ == 'User')

    print(f"Baza: {app.config['SQLALCHEMY_DATABASE_URI']}")
    plain_users = [u for u in User.query.all() if not is_password_hash(u.password)]
    print(f'Kont do zahashowania: {len(plain_users)}')
    for i, user in enumerate(plain_users, 1):
        user.password = hash_password(user.password)
        db.session.commit()  # po każdym koncie, żeby przerwanie nie cofało postępu
        print(f'[{i}/{len(plain_users)}] {user.username}')
    print('Gotowe.')
