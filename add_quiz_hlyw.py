# Jednorazowo: dodaje "Quiz o Hlywie" z pytaniami, które wcześniej były wpisane na sztywno w kodzie (/dodaj_pytania).
# Uruchamiać ręcznie: python add_quiz_hlyw.py. Jeśli quiz o tej nazwie już jest, skrypt nic nie robi.
import json

from app import create_app

TITLE = 'Quiz o Hlywie'
QUESTIONS = [
    ('W którym roku powstał Hlyw?', 'otwarte', None, '2021'),
    ('Podaj liczbę powierzchni użytkowej Hlywa w m²', 'abcd',
     {'a': '15,91 m²', 'b': '16,88 m²', 'c': '14,92 m²', 'd': '17,08 m²'}, 'b'),
    ('Jaką pierwszą rzecz Prezes Hlywu wydrukował na drukarce 3D?', 'abcd',
     {'a': 'Papież', 'b': 'Napis HLYW', 'c': 'Sześcian', 'd': 'BMW'}, 'c'),
    ('Ile Czucz miał lat?', 'abcd', {'a': '16', 'b': '17', 'c': '18', 'd': '19'}, 'a'),
    ('Ile najwięcej osób było jednocześnie w Hlywie?', 'otwarte', None, '23'),
]

app = create_app()

with app.app_context():
    db = app.extensions['sqlalchemy']
    model = {m.class_.__name__: m.class_ for m in db.Model.registry.mappers}
    Quiz, QuizItem = model['Quiz'], model['QuizItem']

    print(f"Baza: {app.config['SQLALCHEMY_DATABASE_URI']}")
    if Quiz.query.filter_by(title=TITLE).first():
        print(f'"{TITLE}" już istnieje - pomijam.')
    else:
        quiz = Quiz(title=TITLE)
        db.session.add(quiz)
        db.session.flush()
        for pos, (text, kind, options, correct) in enumerate(QUESTIONS):
            db.session.add(QuizItem(quiz_id=quiz.id, position=pos, text=text, kind=kind, correct_answer=correct,
                                    options=json.dumps(options, ensure_ascii=False) if options else None))
        db.session.commit()
        print(f'Dodano "{TITLE}" ({len(QUESTIONS)} pytań).')
