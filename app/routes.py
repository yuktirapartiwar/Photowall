from flask import render_template, url_for, flash, redirect, request, jsonify
from app import app, db, bcrypt
from app.forms import RegistrationForm, LoginForm, UploadForm, CategoryForm, AddCategoryToPhotoForm
from app.models import User, Photo, Category, photo_categories
from flask_login import login_user, current_user, logout_user, login_required
import os
import secrets
from PIL import Image

@app.route("/")
@app.route("/home")
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    photos = Photo.query.filter_by(user_id=current_user.id).distinct(Photo.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('home.html', photos=photos, user=current_user, categories=categories)

# Display Photos with is_favorite attribute True in Photo table
@app.route("/favorite")
@login_required
def favorite():
    user = current_user
    photos = Photo.query.filter_by(user_id=current_user.id, is_favorite=True).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('favorite.html', user=user, photos=photos, categories=categories)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_photo(form_photo):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_photo.filename)
    photo_fn = random_hex + f_ext
    photo_path = os.path.join(app.root_path, 'static/images', photo_fn)
    
    output_size = (250, 250)
    i = Image.open(form_photo)
    i.thumbnail(output_size)
    i.save(photo_path)

    return photo_fn

@app.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()
    form.categories.choices = [(category.id, category.name) for category in Category.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        if form.photo.data:
            photo_file = save_photo(form.photo.data)
            photo = Photo(title=form.title.data, image_file=photo_file, user_id=current_user.id)
            db.session.add(photo)

            for category_id in form.categories.data:
                category = Category.query.get(category_id)
                if category:
                    db.session.execute(photo_categories.insert().values(photo_id=photo.id, category_id=category.id, user_id=current_user.id))
            
            db.session.commit()
            flash('Your photo has been uploaded!', 'success')
            return redirect(url_for('home'))
    return render_template('upload.html', form=form)

# Function to update is_favorite attributein the database in Photo table
@app.route("/add_favorite/<int:photo_id>", methods=['GET', 'POST'])
@login_required
def add_favorite(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.is_favorite = True
    db.session.commit()
    return redirect(url_for('home'))

# Function to remove photo from favorites
@app.route("/remove_favorite/<int:photo_id>", methods=['GET', 'POST'])
@login_required
def remove_favorite(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.is_favorite = False
    db.session.commit()
    return redirect(url_for('favorite'))

# Function to delete photo from database
@app.route("/delete_photo/<int:photo_id>", methods=['GET', 'POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/create_category", methods=['GET', 'POST'])
@login_required
def create_category():
    form = CategoryForm()
    if form.validate_on_submit():
        print("Form validated successfully")
        print("Form data:", form.data)

        category = Category(name=form.name.data, user_id=current_user.id)
        db.session.add(category)
        db.session.commit()
        print("Category ID:", category.id)  # Check if the category is created with an ID
        
        return redirect(url_for('home'))
    else:
        print("Form validation failed")
        print("Errors:", form.errors)
    return render_template('create_category.html', title='Create Category', form=form)

@app.route("/add_to_category/<int:photo_id>", methods=['GET', 'POST'])
@login_required
def add_category_to_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    form = AddCategoryToPhotoForm()
    form.categories.choices = [(category.id, category.name) for category in Category.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        selected_categories = form.categories.data
        for category_id in selected_categories:
            category = Category.query.get(category_id)
            if category:
                if not db.session.query(photo_categories).filter_by(photo_id=photo.id, category_id=category.id).first():
                    db.session.execute(photo_categories.insert().values(photo_id=photo.id, category_id=category.id, user_id=current_user.id))
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_category_to_photo.html', title='Add to Category', form=form, photo=photo)

@app.route("/category/<int:category_id>")
@login_required
def category_photos(category_id):
    category = Category.query.get_or_404(category_id)
    photos = Photo.query.join(Photo.categories).filter(Category.id == category_id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('category_photos.html', title=category.name, photos=photos, categories=categories)