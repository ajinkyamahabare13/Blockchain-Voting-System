from flask import Flask, render_template, request, redirect, session, flash
from models import db, User, Candidate, Election, Transaction
from blockchain import vote as cast_vote, get_candidate, get_candidate_count, web3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "blockchain_voting_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voting.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

import os

with app.app_context():

    db.create_all()

    # Create Election record if it doesn't exist
    if Election.query.first() is None:

        election = Election(is_active=False)

        db.session.add(election)

        db.session.commit()

    print("=" * 50)
    print("Blockchain Voting System Started Successfully")
    print("=" * 50)
    print("Database Location:")
    print(os.path.abspath(db.engine.url.database))
    print("=" * 50)


# ==========================
# Home
# ==========================
@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# Register
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        wallet_address = request.form["wallet_address"]

        # Secure Password Hashing
        hashed_password = generate_password_hash(
            request.form["password"],
            method="pbkdf2:sha256"
        )

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered!", "danger")
            return redirect("/register")

        # Create new user
        new_user = User(
    full_name=full_name,
    email=email,
    password=hashed_password,
    wallet_address=wallet_address,
    is_admin=(email == "admin@gmail.com")
)

        db.session.add(new_user)
        db.session.commit()

        flash("Registration Successful! Please Login.", "success")
        return redirect("/login")

    return render_template("register.html")


# ==========================
# Login
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id

            flash("Welcome Back!", "success")

            return redirect("/dashboard")

        flash("Invalid Email or Password!", "danger")
        return redirect("/login")
    return render_template("login.html")


# ==========================
# Dashboard
# ==========================
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    candidates = Candidate.query.all()

    total_users = User.query.count()
    total_candidates = Candidate.query.count()
    total_votes = sum(c.votes for c in candidates)

    blockchain_status = web3.is_connected()

    # Chart Data
    chart_labels = [c.name for c in candidates]
    chart_votes = [c.votes for c in candidates]

    return render_template(
        "dashboard.html",
        user=user,
        total_users=total_users,
        total_candidates=total_candidates,
        total_votes=total_votes,
        blockchain_status=blockchain_status,
        chart_labels=chart_labels,
        chart_votes=chart_votes
    )


# ==========================
# Admin Panel
# ==========================
@app.route("/admin", methods=["GET", "POST"])
def admin():

    # User must be logged in
    if "user_id" not in session:
        return redirect("/login")

    # Logged in user
    user = User.query.get(session["user_id"])

    # Only admins can access
    if not user.is_admin:
        flash("Access Denied! Admins only.", "danger")
        return redirect("/dashboard")

    # ==========================
    # Add Candidate
    # ==========================
    if request.method == "POST":

        name = request.form["name"]
        party = request.form["party"]

        candidate = Candidate(
            name=name,
            party=party
        )

        db.session.add(candidate)
        db.session.commit()

        flash("Candidate Added Successfully!", "success")

        return redirect("/admin")

    # ==========================
    # Dashboard Statistics
    # ==========================

    candidates = Candidate.query.all()

    total_candidates = Candidate.query.count()

    total_users = User.query.count()

    total_votes = sum(candidate.votes for candidate in candidates)

    remaining_voters = total_users - total_votes

    if total_users > 0:
        voting_percentage = round((total_votes / total_users) * 100, 2)
    else:
        voting_percentage = 0

    blockchain_status = web3.is_connected()
    election = Election.query.first()

    # Winner
    winner = None
    if candidates:
        winner = max(candidates, key=lambda c: c.votes)

    # Lowest Candidate
    lowest_candidate = None
    if candidates:
        lowest_candidate = min(candidates, key=lambda c: c.votes)

    # Chart Data
    chart_labels = [c.name for c in candidates]
    chart_votes = [c.votes for c in candidates]

    return render_template(
        "admin.html",
        candidates=candidates,
        total_candidates=total_candidates,
        total_users=total_users,
        total_votes=total_votes,
        remaining_voters=remaining_voters,
        voting_percentage=voting_percentage,
        blockchain_status=blockchain_status,
        winner=winner,
        lowest_candidate=lowest_candidate,
        chart_labels=chart_labels,
        chart_votes=chart_votes,
        election=election
    )
# ==========================
# Delete Candidate
# ==========================

@app.route("/delete_candidate/<int:id>")
def delete_candidate(id):

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Unauthorized Access!", "danger")
        return redirect("/dashboard")

    candidate = Candidate.query.get_or_404(id)

    db.session.delete(candidate)
    db.session.commit()

    flash("Candidate Deleted Successfully!", "success")

    return redirect("/admin")

# ==========================
# Edit Candidate
# ==========================
@app.route("/edit_candidate/<int:id>", methods=["GET", "POST"])
def edit_candidate(id):

    # User must be logged in
    if "user_id" not in session:
        return redirect("/login")

    # Get logged-in user
    user = User.query.get(session["user_id"])

    # Only admin can edit candidates
    if not user.is_admin:
        flash("Unauthorized Access!", "danger")
        return redirect("/dashboard")

    # Get candidate
    candidate = Candidate.query.get_or_404(id)

    # Update candidate
    if request.method == "POST":

        candidate.name = request.form["name"]
        candidate.party = request.form["party"]

        db.session.commit()

        flash("Candidate Updated Successfully!", "success")

        return redirect("/admin")

    return render_template(
        "edit_candidate.html",
        candidate=candidate
    )

# ==========================
# Start Election
# ==========================
@app.route("/start_election")
def start_election():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Unauthorized Access!", "danger")
        return redirect("/dashboard")

    election = Election.query.first()

    election.is_active = True

    db.session.commit()

    flash("Election Started Successfully!", "success")

    return redirect("/admin")


# ==========================
# Stop Election
# ==========================
@app.route("/stop_election")
def stop_election():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Unauthorized Access!", "danger")
        return redirect("/dashboard")

    election = Election.query.first()

    election.is_active = False

    db.session.commit()

    flash("Election Stopped Successfully!", "warning")

    return redirect("/admin")


# ==========================
# Vote
# ==========================
@app.route("/vote", methods=["GET", "POST"])
def vote_page():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])
    # Check Election Status
    election = Election.query.first()

    if election is None or not election.is_active:
        flash("Election is currently closed.", "warning")
        return redirect("/dashboard")



    if user.has_voted:
        flash("You have already voted!", "warning")
        return redirect("/dashboard")

    if request.method == "POST":

        candidate_id = int(request.form["candidate_id"])

        candidate = Candidate.query.get(candidate_id)

        if not candidate:
            flash("Candidate not found!", "danger")
            return redirect("/vote")

        try:

            # Blockchain Vote
            tx_hash = cast_vote(candidate_id)

            # Local Database
            candidate.votes += 1
            user.has_voted = True

            # Save Blockchain Transaction
            transaction = Transaction(
               voter_name=user.full_name,
               candidate_name=candidate.name,
               tx_hash=str(tx_hash)
            )

            db.session.add(transaction)

            db.session.commit()

            session["tx_hash"] = str(tx_hash)
            session["candidate_name"] = candidate.name
            flash("Vote Cast Successfully!", "success")

            return redirect("/vote_success")

        except Exception as e:

            db.session.rollback()

            flash(f"Blockchain Error: {str(e)}", "danger")

            return redirect("/vote")

    candidates = Candidate.query.all()

    return render_template(
        "vote.html",
        candidates=candidates
    )


# ==========================
# Vote Success
# ==========================
@app.route("/vote_success")
def vote_success():

    if "user_id" not in session:
        return redirect("/login")

    tx_hash = session.get("tx_hash")
    candidate_name = session.get("candidate_name")

    return render_template(
        "vote_success.html",
        tx_hash=tx_hash,
        candidate_name=candidate_name
    )


# ==========================
# Results
# ==========================
@app.route("/results")
def results():

    candidates = Candidate.query.all()

    total_votes = sum(candidate.votes for candidate in candidates)

    winner = None

    if candidates:
        winner = max(candidates, key=lambda c: c.votes)

    chart_labels = [candidate.name for candidate in candidates]
    chart_votes = [candidate.votes for candidate in candidates]

    return render_template(
        "results.html",
        candidates=candidates,
        total_votes=total_votes,
        winner=winner,
        chart_labels=chart_labels,
        chart_votes=chart_votes
    )

@app.route("/transactions")
def transactions():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Access Denied!", "danger")
        return redirect("/dashboard")

    transactions = Transaction.query.order_by(
        Transaction.timestamp.desc()
    ).all()

    return render_template(
        "transactions.html",
        transactions=transactions
    )

# ==========================
# Logout
# ==========================
@app.route("/logout")
def logout():

    session.clear()

    flash("Logged Out Successfully!", "info")

    return redirect("/login")

# ==========================
# Main
# ==========================
if __name__ == "__main__":
    app.run(debug=True)  