from wsgi import app, serializer
from models import db, User, SocialLink, InteractionType, InteractionRequest, Interaction, VisibilityState
from forms import RegistrationForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash, render_template, redirect, url_for, request, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from functools import wraps
import uuid
from PIL import Image
import base64
from io import BytesIO
from utils import send_verification_email

def logged_out_only(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))  # Replace 'home' with your desired route
        return view_function(*args, **kwargs)
    return decorated_function

def verified_only(view_function):
    @login_required
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not current_user.email_verified:
            flash("You have been sent verification email. Follow the link to use the service")
            return redirect(url_for('unverified'))  # Replace 'home' with your desired route
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
        avatar_url = ""
        if form.photo.data:
            try:
                # Decode Base64 data
                avatar_data = form.photo.data.split(",")[1]  # Remove the Base64 header
                avatar_bytes = base64.b64decode(avatar_data)
    
                # Load the image with Pillow
                img = Image.open(BytesIO(avatar_bytes))
    
                # Save the processed image
                avatar_path = f'/static/uploads/{uuid.uuid4().hex}.png'
                avatar_url = avatar_path
                img.save(avatar_path, 'PNG')
    
            except Exception as e:
                flash(f"Failed to process avatar", "danger")

        # Add user to the database
        new_user = User(username=username, email=email, password_hash=password, photo_url=avatar_url)

        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()  # Rollback the session to prevent conflicts
            # Check which field caused the issue
            if User.query.filter_by(username=username).first():
                flash("Username is already taken. Please choose a different one.", "danger")
            elif User.query.filter_by(email=email).first():
                flash("Email is already registered. Please use a different email.", "danger")
            else:
                flash("An unexpected error occurred. Please try again.", "danger")
            return render_template('register.html', form=form)

        flash('You have been sent a verification email. Follow the link to verify.', 'success')

        login_user(new_user)
        send_verification_email(new_user)

        return redirect(url_for('unverified'))  # Redirect to graph page

    return render_template('register.html', form=form)

@app.route('/unverified', methods=['GET', 'POST'])
@login_required
def unverified():
    if current_user.email_verified:
        return redirect(url_for('dashboard'))  # Redirect if already verified
    if request.method == 'POST':
        send_verification_email(current_user)
        flash("Verification email has been resent.", "success")
    return render_template('unverified.html')

@app.route('/verify_email/<token>')
def verify_email(token):
    try:
        email = serializer.loads(token, salt='email-confirmation', max_age=3600)  # Token expires in 1 hour
        user = User.query.filter_by(email=email).first_or_404()
        user.email_verified = True
        db.session.commit()
        flash("Email verified successfully", "success")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash("Verification link expired", "danger")
        return redirect(url_for('unverified'))


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
@verified_only
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
    if own_page:
        social_links = SocialLink.query.filter_by(user_id=user.id).all()
    else:   
        social_links = SocialLink.query.filter_by(user_id=user.id) \
            .filter_by(visibility=VisibilityState.VISIBLE).all()

    social_links = sorted(social_links, key=lambda x: x.platform)
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

@app.route('/update_visibility', methods=['POST'])
@verified_only
def update_visibility():
    item = request.args.get('item')
    visibility = request.form.get('visibility')

    if visibility not in ['VISIBLE', 'HIDDEN', 'SEARCH_ONLY']:
        flash("Invalid visibility option", "danger")
        return redirect(url_for('dashboard'))

    if item == 'email':
        current_user.email_visibility = VisibilityState[visibility]
    elif item == 'social':
        link_id = request.args.get('id')
        link = SocialLink.query.get_or_404(link_id)
        if link.user_id != current_user.id:
            flash("You are not authorized to edit this link", "danger")
            return redirect(url_for('dashboard'))
        link.visibility = VisibilityState[visibility]

    db.session.commit()
    flash("Visibility updated successfully", "success")
    return redirect(url_for('dashboard'))


@app.route('/graph')
@verified_only
def graph():
    # Fetch all users and interactions
    users = User.query.all()
    nodes = [{"id": user.id, "name": user.username, "avatar": user.photo_url } for user in users]
    interaction_types = InteractionType.query.all()

    return render_template('graph.html', nodes=nodes, interaction_types=interaction_types)

@app.route('/interactions', methods=['GET'])
@verified_only
def interactions():
    # Get the list of interaction type IDs from the request
    type_ids = request.args.getlist('type_id')

    if type_ids:
        # Query interactions filtered by type if provided
        query = Interaction.query
        query = query.filter(Interaction.type_id.in_(type_ids))
        interactions = query.all()
    else:
        interactions = []
    
    unique_edges = {}
    for interaction in interactions:
        pair = tuple(sorted([interaction.user_1_id, interaction.user_2_id]))
        if pair not in unique_edges:
            unique_edges[pair] = {"source": pair[0], "target": pair[1], "type_id": interaction.type_id}

    links = list(unique_edges.values())
    return jsonify(links)

@app.route('/request_interaction/<int:target_id>', methods=['POST'])
@verified_only
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
@verified_only
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

@app.route('/decline_request/<int:request_id>', methods=['POST'])
@verified_only
def decline_request(request_id):
    # Fetch the interaction request
    interaction_request = InteractionRequest.query.get_or_404(request_id)

    # Ensure the current user is the target of the request
    if interaction_request.target_id != current_user.id:
        flash('You are not authorized to decline this request.', 'danger')
        return redirect(url_for('dashboard'))

    # Update the request status
    interaction_request.status = 'declined'
    db.session.commit()

    flash('Interaction request declined.', 'info')
    return redirect(url_for('dashboard'))