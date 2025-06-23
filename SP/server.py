# server.py
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
import os
from PIL import Image as PILImage    # for converting PNG → JPEG

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'tajny_klucz_demo'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


class User(db.Model):
    id       = db.Column(db.Integer,   primary_key=True)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    username = db.Column(db.String(120), nullable=True)
    bio      = db.Column(db.Text,       nullable=True)


class Image(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename    = db.Column(db.String(256), unique=True, nullable=False)
    description = db.Column(db.Text,       nullable=True)
    uploaded_at = db.Column(db.DateTime,   default=datetime.datetime.utcnow)


class Album(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'))
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text,      nullable=True)
    created_at  = db.Column(db.DateTime,  default=datetime.datetime.utcnow)


class AlbumImage(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    album_id    = db.Column(db.Integer, db.ForeignKey('album.id'))
    filename    = db.Column(db.String(256), unique=True, nullable=False)
    description = db.Column(db.Text,      nullable=True)
    uploaded_at = db.Column(db.DateTime,  default=datetime.datetime.utcnow)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith("Bearer "):
            return jsonify({'error': 'Brak tokenu'}), 401
        token = auth.split(" ", 1)[1]
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['id'])
            if not current_user:
                raise RuntimeError("Użytkownik nie istnieje")
        except Exception as e:
            return jsonify({'error': 'Nieprawidłowy token', 'details': str(e)}), 401
        return f(current_user, *args, **kwargs)
    return decorated


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')
    if not email or not password:
        return jsonify({'error': 'Email i hasło wymagane'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Użytkownik już istnieje'}), 409
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password=hashed_pw)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Zarejestrowano'}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(email=data.get('email','')).first()
    if user and bcrypt.check_password_hash(user.password, data.get('password','')):
        token = jwt.encode({
            'id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token, 'email': user.email}), 200
    return jsonify({'error': 'Błędne dane logowania'}), 401


@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'username': current_user.username or current_user.email,
        'bio': current_user.bio or ""
    }), 200


@app.route('/api/profile-edit', methods=['POST'])
@token_required
def edit_profile(current_user):
    data = request.get_json() or {}
    if 'username' in data:
        current_user.username = data['username']
    if 'bio' in data:
        current_user.bio = data['bio']
    db.session.commit()
    return jsonify({
        'message': 'Profile updated',
        'username': current_user.username,
        'bio': current_user.bio
    }), 200


@app.route('/api/profile-picture', methods=['POST'])
@token_required
def upload_profile_picture(current_user):
    if 'file' not in request.files:
        return jsonify({'error': 'Brak pliku'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nie wybrano pliku'}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png'):
        return jsonify({'error': 'Dozwolone tylko JPG/JPEG/PNG'}), 400
    try:
        img = PILImage.open(file.stream).convert('RGB')
        save_name = f"profile_{current_user.id}.jpg"
        img.save(os.path.join(UPLOAD_FOLDER, save_name), format='JPEG', quality=85)
    except Exception as e:
        return jsonify({'error': 'Błąd przetwarzania obrazu', 'details': str(e)}), 500
    return jsonify({'message': 'Zdjęcie profilowe zapisane'}), 200


@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file(current_user):
    if 'file' not in request.files:
        return jsonify({'error': 'Brak pliku'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nie wybrano pliku'}), 400
    description = request.form.get('description', '')
    filename = f"user{current_user.id}_{file.filename}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    image = Image(user_id=current_user.id, filename=filename, description=description)
    db.session.add(image)
    db.session.commit()
    return jsonify({'message': 'Plik został zapisany'}), 200


@app.route('/api/images', methods=['GET'])
@token_required
def get_user_images(current_user):
    images = Image.query.filter_by(user_id=current_user.id)\
                       .order_by(Image.uploaded_at.desc())\
                       .all()
    return jsonify([{
        'filename': img.filename,
        'description': img.description,
        'uploaded_at': img.uploaded_at.strftime('%Y-%m-%d %H:%M')
    } for img in images]), 200


@app.route('/api/images/<filename>', methods=['DELETE'])
@token_required
def delete_image(current_user, filename):
    img = Image.query.filter_by(filename=filename, user_id=current_user.id).first()
    if not img:
        return jsonify({'error': 'Image not found or not yours'}), 404

    # remove file from disk
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            return jsonify({'error': 'Could not delete file', 'details': str(e)}), 500

    # remove from DB
    db.session.delete(img)
    db.session.commit()
    return jsonify({'message': 'Image deleted'}), 200


# —————— Albums endpoints ——————

@app.route('/api/albums', methods=['GET'])
@token_required
def list_albums(current_user):
    albums = Album.query.filter_by(user_id=current_user.id)\
                        .order_by(Album.created_at.desc())\
                        .all()
    return jsonify([{
        'id': alb.id,
        'name': alb.name,
        'description': alb.description,
        'created_at': alb.created_at.isoformat()
    } for alb in albums]), 200


@app.route('/api/albums', methods=['POST'])
@token_required
def create_album(current_user):
    data = request.get_json() or {}
    name = data.get('name','').strip()
    if not name:
        return jsonify({'error':'Album needs a name'}), 400
    alb = Album(user_id=current_user.id,
                name=name,
                description=data.get('description',''))
    db.session.add(alb)
    db.session.commit()
    return jsonify({
        'id': alb.id,
        'name': alb.name,
        'description': alb.description,
        'created_at': alb.created_at.isoformat()
    }), 201


@app.route('/api/albums/<int:aid>/images', methods=['GET'])
@token_required
def list_album_images(current_user, aid):
    alb = Album.query.get_or_404(aid)
    if alb.user_id != current_user.id:
        return jsonify({'error':'Forbidden'}), 403
    imgs = AlbumImage.query.filter_by(album_id=aid)\
                            .order_by(AlbumImage.uploaded_at.desc())\
                            .all()
    return jsonify([{
        'filename': img.filename,
        'description': img.description,
        'uploaded_at': img.uploaded_at.strftime('%Y-%m-%d %H:%M')
    } for img in imgs]), 200


@app.route('/api/albums/<int:aid>/images', methods=['POST'])
@token_required
def add_image_to_album(current_user, aid):
    alb = Album.query.get_or_404(aid)
    if alb.user_id != current_user.id:
        return jsonify({'error':'Forbidden'}), 403
    if 'file' not in request.files:
        return jsonify({'error':'Brak pliku'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error':'Nie wybrano pliku'}), 400
    desc = request.form.get('description','')
    filename = f"album{aid}_{file.filename}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    ai = AlbumImage(album_id=aid, filename=filename, description=desc)
    db.session.add(ai)
    db.session.commit()
    return jsonify({
        'filename': ai.filename,
        'description': ai.description,
        'uploaded_at': ai.uploaded_at.strftime('%Y-%m-%d %H:%M')
    }), 201


@app.route('/uploads/<path:filename>', methods=['GET'])
def get_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/api/secure', methods=['GET'])
@token_required
def secure(current_user):
    return jsonify({'message': f'Zalogowano jako {current_user.email}'}), 200


if __name__ == '__main__':
    if not os.path.exists('users.db'):
        with app.app_context():
            db.create_all()
            print("🧱 Baza danych utworzona.")
    app.run(port=3000, debug=True)
