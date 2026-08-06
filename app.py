from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from blockchain import web3, vote as cast_vote, get_candidate, get_candidate_count
from models import db, User, Candidate, Election, Transaction

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "blockchain_voting_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voting.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

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

        photo = request.files["photo"]

        filename = photo.filename

        photo.save(os.path.join("static", "uploads", filename))

        # DEBUG
        print("Name:", name)
        print("Party:", party)
        print("Photo:", filename)

        candidate = Candidate(
           name=name,
           party=party,
           photo=filename
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

    # Blockchain Transactions
    transactions = Transaction.query.order_by(
        Transaction.id.desc()
    ).all()

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
        election=election,
        transactions=transactions
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
            tx_hash = cast_vote(candidate_id - 1)

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

          print("=" * 60)
          print("BLOCKCHAIN ERROR")
          print(e)
          print("=" * 60)

          raise e

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

    total = get_candidate_count()

    candidates = []

    total_votes = 0

    for i in range(total):

        data = get_candidate(i)

        total_votes += data[3]

        candidates.append({
            "id": data[0] + 1,
            "name": data[1],
            "party": data[2],
            "votes": data[3]
        })

    winner = None

    if candidates:
        winner = max(candidates, key=lambda x: x["votes"])
        # Runner-up
    runner_up = None

    if len(candidates) >= 2:

        sorted_candidates = sorted(
          candidates,
          key=lambda x: x["votes"],
          reverse=True
        )

        winner = sorted_candidates[0]
        runner_up = sorted_candidates[1]

    # Total registered users
    total_users = User.query.count()

    # Voting percentage
    voting_percentage = 0

    if total_users > 0:
       voting_percentage = round((total_votes / total_users) * 100, 2)

    # Election Status
    election = Election.query.first()

    election_status = "Closed"

    if election and election.is_active:
      election_status = "Open"

    # Winning Margin
    winning_margin = 0

    if winner and runner_up:
      winning_margin = winner["votes"] - runner_up["votes"]

    chart_labels = [candidate["name"] for candidate in candidates]
    chart_votes = [candidate["votes"] for candidate in candidates]

    return render_template(
    "results.html",
    candidates=candidates,
    total_votes=total_votes,
    winner=winner,
    runner_up=runner_up,
    chart_labels=chart_labels,
    chart_votes=chart_votes,
    total_users=total_users,
    voting_percentage=voting_percentage,
    election_status=election_status,
    winning_margin=winning_margin
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
# Reset Election
# ==========================

@app.route("/reset_election")
def reset_election():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Access Denied!", "danger")
        return redirect("/dashboard")

    # Reset Candidate Votes
    candidates = Candidate.query.all()

    for candidate in candidates:
        candidate.votes = 0

    # Reset Users
    users = User.query.all()

    for u in users:
        u.has_voted = False

    # Delete Transaction History
    Transaction.query.delete()

    # Close Election
    election = Election.query.first()

    if election:
        election.is_active = False

    db.session.commit()

    flash("Election Reset Successfully!", "success")

    return redirect("/admin")

@app.route("/export_pdf")
def export_pdf():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Access Denied!", "danger")
        return redirect("/dashboard")

    candidates = Candidate.query.all()

    pdf = SimpleDocTemplate("Election_Result_Report.pdf")

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph("<b>Blockchain Voting System</b>", styles["Title"])
    )

    elements.append(
        Paragraph("Election Result Report", styles["Heading2"])
    )

    data = [["Candidate", "Party", "Votes"]]

    for candidate in candidates:
        data.append([
            candidate.name,
            candidate.party,
            str(candidate.votes)
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BOTTOMPADDING", (0,0), (-1,0), 12)
    ]))

    elements.append(table)

    pdf.build(elements)

    flash("Election_Result_Report.pdf generated successfully!", "success")

    return redirect("/admin")
# ==========================
# Export Results to Excel
# ==========================

@app.route("/export_excel")
def export_excel():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Access Denied!", "danger")
        return redirect("/dashboard")

    candidates = Candidate.query.all()

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Election Results"

    # Heading
    sheet.append(["Candidate Name", "Party", "Votes"])

    # Candidate Data
    for candidate in candidates:

        sheet.append([
            candidate.name,
            candidate.party,
            candidate.votes
        ])

    workbook.save("Election_Result_Report.xlsx")

    flash("Election_Result_Report.xlsx generated successfully!", "success")

    return redirect("/admin")
# ==========================
# Logout
# ==========================
@app.route("/logout")
def logout():

    session.clear()

    flash("Logged Out Successfully!", "info")

    return redirect("/login")


#Download Report

@app.route("/download_report")
def download_report():

    # Admin check
    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        flash("Access Denied!", "danger")
        return redirect("/dashboard")

    candidates = Candidate.query.all()

    total_users = User.query.count()
    total_votes = sum(c.votes for c in candidates)

    voting_percentage = 0
    if total_users > 0:
        voting_percentage = round((total_votes / total_users) * 100, 2)

    winner = None
    runner_up = None

    if candidates:
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x.votes,
            reverse=True
        )

        winner = sorted_candidates[0]

        if len(sorted_candidates) > 1:
            runner_up = sorted_candidates[1]

    filename = "Election_Report.pdf"

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b>BLOCKCHAIN VOTING SYSTEM</b>", styles["Title"]))
    story.append(Paragraph("Election Final Report", styles["Heading2"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph(f"Generated : {datetime.now()}", styles["Normal"]))
    story.append(Paragraph(f"Registered Users : {total_users}", styles["Normal"]))
    story.append(Paragraph(f"Votes Cast : {total_votes}", styles["Normal"]))
    story.append(Paragraph(f"Voting Percentage : {voting_percentage}%", styles["Normal"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

    if winner:
        story.append(
            Paragraph(
                f"<b>Winner :</b> {winner.name} ({winner.party}) - {winner.votes} Votes",
                styles["Heading2"]
            )
        )

    if runner_up:
        story.append(
            Paragraph(
                f"<b>Runner-up :</b> {runner_up.name} ({runner_up.party}) - {runner_up.votes} Votes",
                styles["Heading2"]
            )
        )

    story.append(Paragraph("<br/>", styles["Normal"]))
    story.append(Paragraph("<b>Candidate Results</b>", styles["Heading2"]))

    for c in candidates:

        story.append(
            Paragraph(
                f"{c.name} | {c.party} | Votes : {c.votes}",
                styles["Normal"]
            )
        )

    doc.build(story)

    return send_file(
        filename,
        as_attachment=True
    )


# ==========================
# Main
# ==========================
if __name__ == "__main__":
    app.run(debug=True)  