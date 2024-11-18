from wsgi import app
from models import db, User, SocialLink, InteractionType, InteractionRequest, Interaction
from forms import RegistrationForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash, render_template, redirect, url_for, request
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import func
from functools import wraps

def logged_out_only(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))  # Replace 'home' with your desired route
        return view_function(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
@logged_out_only
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
@logged_out_only
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = generate_password_hash(form.password.data)
        
        # Handle optional photo
        photo_url = None
        if form.photo.data:
            # Save the uploaded photo (e.g., to static/uploads directory)
            photo = form.photo.data
            photo_filename = f"{username}_{photo.filename}"
            photo.save(f"/static/uploads/{photo_filename}")
            photo_url = f"/static/uploads/{photo_filename}"

        # Add user to the database
        new_user = User(username=username, email=email, password_hash=password, photo_url=photo_url)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful!', 'success')

        login_user(new_user)

        return redirect(url_for('dashboard'))  # Redirect to graph page

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
@logged_out_only
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Query user by email
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)  # Log in the user
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to dashboard or home page
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('register'))  # Redirect to register or login page

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        platform = request.form.get('platform')
        link = request.form.get('link')

        if platform and link:
            # Add new social link
            new_social_link = SocialLink(user_id=current_user.id, platform=platform, link=link)
            db.session.add(new_social_link)
            db.session.commit()
            flash(f'Social network "{platform}" added successfully!', 'success')

        return redirect(url_for('dashboard'))
    
    if 'user_id' in request.args and request.args['user_id'] != current_user.get_id():
        user = User.query.filter_by(id=request.args['user_id']).first()
        own_page = False
    else:
        user = current_user
        own_page = True
    # Fetch existing social links
    social_links = SocialLink.query.filter_by(user_id=user.id).all()

    # Fetch interaction statistics
    interaction_stats = (
        db.session.query(Interaction.type_id, InteractionType.name, func.count(Interaction.id))
        .join(InteractionType, Interaction.type_id == InteractionType.id)
        .filter((Interaction.user_1_id == user.id) | (Interaction.user_2_id == user.id))
        .group_by(Interaction.type_id, InteractionType.name)
        .all()
    )

    stats = [{"type": type_name, "count": count} for _, type_name, count in interaction_stats]

    # Fetch interaction types for the dropdown
    interaction_types = InteractionType.query.all()

    # Fetch pending incoming requests for this user
    incoming_requests = (
        InteractionRequest.query
        .filter_by(target_id=user.id, status='pending')
        .join(InteractionType, InteractionRequest.type_id == InteractionType.id)
        .add_columns(InteractionRequest.id, InteractionRequest.message, InteractionType.name, User.username, User.id.label("requester_id"))
        .join(User, InteractionRequest.requester_id == User.id)
        .all()
    )

    return render_template(
        'dashboard.html',
        user=user,
        own_page=own_page,
        social_links=social_links,
        stats=stats,
        interaction_types=interaction_types,
        incoming_requests=incoming_requests
    )

@app.route('/graph')
@login_required
def graph():
    # Fetch all users and interactions
    users = User.query.all()
    interactions = Interaction.query.all()

    # Prepare data for graph
    nodes = [{"id": user.id, "name": user.username, "avatar": user.photo_url } for user in users]
    links = [
        {"source": interaction.user_1_id, "target": interaction.user_2_id}
        for interaction in interactions
    ]

    return render_template('graph.html', nodes=nodes, links=links)

@app.route('/request_interaction/<int:target_id>', methods=['POST'])
@login_required
def request_interaction(target_id):
    interaction_type_id = request.form.get('interaction_type')
    message = request.form.get('message')

    if not interaction_type_id:
        flash('Please select an interaction type.', 'danger')
        return redirect(url_for('dashboard', user_id=target_id))

    # Create a new interaction request
    interaction_request = InteractionRequest(
        requester_id=current_user.id,
        target_id=target_id,
        type_id=interaction_type_id,
        message=message,
        status='pending'
    )

    db.session.add(interaction_request)
    db.session.commit()
    flash('Interaction request sent successfully!', 'success')
    return redirect(url_for('dashboard') + f"?user_id={target_id}")

@app.route('/approve_request/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    # Fetch the interaction request
    interaction_request = InteractionRequest.query.get_or_404(request_id)

    # Ensure the current user is the target of the request
    if interaction_request.target_id != current_user.id:
        flash('You are not authorized to approve this request.', 'danger')
        return redirect(url_for('dashboard'))

    # Add the interaction
    new_interaction = Interaction(
        user_1_id=interaction_request.requester_id,
        user_2_id=interaction_request.target_id,
        type_id=interaction_request.type_id
    )
    db.session.add(new_interaction)

    # Update the request status
    interaction_request.status = 'approved'
    db.session.commit()

    flash('Interaction request approved and interaction added!', 'success')
    return redirect(url_for('dashboard'))