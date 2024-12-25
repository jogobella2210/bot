from flask import Flask, render_template, request

app = Flask(__name__)

# Головна сторінка мінізастосунка
@app.route('/')
def index():
    # Приклад даних, які можна відобразити
    task = request.args.get('task', 'Немає завдань')
    solution = request.args.get('solution', 'Рішення поки немає.')
    return render_template('index.html', task=task, solution=solution)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
