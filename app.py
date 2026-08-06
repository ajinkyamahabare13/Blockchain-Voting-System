from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    session,
    send_file
)

from flask_wtf.csrf import (
    CSRFProtect,
    CSRFError
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from datetime import datetime

import os
import uuid
from dotenv import load_dotenv

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from openpyxl import Workbook

from blockchain import (
    web3,
    contract,
    vote as cast_vote,
    get_candidate,
    get_candidate_count,
    reset_election as reset_blockchain_election,
    add_candidate
)

from models import (
    db,
    User,
    Candidate,
    Election,
    Transaction
)

from auth import (
    login_required,
    admin_required
)

load_dotenv()

app = Flask(__name__)
ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}
app.config.from_pyfile("config.py")
csrf = CSRFProtect(app)

@app.errorhandler(CSRFError)
def handle_csrf_error(error):

    flash(
        "Security validation failed. Please try again.",
        "danger"
    )

    return redirect("/login")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
def allowed_file(filename):

      return (
         "." in filename
         and filename.rsplit(".", 1)[1].lower()
         in ALLOWED_EXTENSIONS
     )
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

    return render_template(
        "index.html"
    )


# ==========================
# Registration
# ==========================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        # ==========================
        # Get Registration Data
        # ==========================

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        wallet_address = request.form.get(
            "wallet_address",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # ==========================
        # Validate Full Name
        # ==========================

        if not full_name:

            flash(
                "Full name is required!",
                "danger"
            )

            return redirect("/register")

        if len(full_name) > 100:

            flash(
                "Full name is too long!",
                "danger"
            )

            return redirect("/register")

        # ==========================
        # Validate Email
        # ==========================

        if not email or "@" not in email:

            flash(
                "Please enter a valid email address!",
                "danger"
            )

            return redirect("/register")

        if len(email) > 100:

            flash(
                "Email address is too long!",
                "danger"
            )

            return redirect("/register")

        # ==========================
        # Validate Wallet Address
        # ==========================

        if not wallet_address:

            flash(
                "Wallet address is required!",
                "danger"
            )

            return redirect("/register")

        if not web3.is_address(
            wallet_address
        ):

            flash(
                "Invalid Ethereum wallet address!",
                "danger"
            )

            return redirect("/register")

        # ==========================
        # Validate Password
        # ==========================

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters!",
                "danger"
            )

            return redirect("/register")

        # ==========================
        # Check Existing User
        # ==========================

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "Email already registered!",
                "danger"
            )

            return redirect("/register")

        # ==========================
        # Hash Password
        # ==========================

        hashed_password = generate_password_hash(
            password,
            method="pbkdf2:sha256"
        )

        # ==========================
        # Create User
        # ==========================

        new_user = User(
            full_name=full_name,
            email=email,
            password=hashed_password,
            wallet_address=wallet_address,
            is_admin=False
        )

        # ==========================
        # Save User to Database
        # ==========================

        try:

            db.session.add(
                new_user
            )

            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print("=" * 60)
            print("USER REGISTRATION DATABASE ERROR")
            print(e)
            print("=" * 60)

            flash(
                "Registration failed. Please try again.",
                "danger"
            )

            return redirect("/register")

        # ==========================
        # Registration Success
        # ==========================

        flash(
            "Registration Successful!",
            "success"
        )

        return redirect("/login")

    # ==========================
    # Registration Page
    # ==========================

    return render_template(
        "register.html"
    )


# ==========================
# Login
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:

            flash(
                "Email and password are required!",
                "warning"
            )

            return redirect("/login")

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session["user_id"] = user.id

            flash(
                "Welcome Back!",
                "success"
            )

            return redirect("/dashboard")

        flash(
            "Invalid Email or Password!",
            "danger"
        )

        return redirect("/login")

    return render_template("login.html")


# ==========================
# Dashboard
# ==========================
@app.route("/dashboard")
@login_required
def dashboard():


    user = db.session.get(
    User,
    session["user_id"]
)

    candidates = Candidate.query.all()

    total_users = User.query.count()
    total_candidates = Candidate.query.count()
    total_votes = sum(c.votes for c in candidates)

    # ==========================
    # Blockchain Status
    # ==========================

    blockchain_status = False

    try:

          if web3.is_connected():

           contract_code = web3.eth.get_code(
            contract.address
        )

          if len(contract_code) > 0:
            blockchain_status = True

    except Exception as e:

     print("Blockchain Status Error:", e)

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

# ==========================
# Admin Dashboard
# ==========================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
@admin_required
def admin():

    # ==========================
    # Add Candidate
    # ==========================

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        party = request.form.get(
            "party",
            ""
        ).strip()

        # --------------------------
        # Validate Candidate Details
        # --------------------------

        if not name or not party:

            flash(
                "Candidate name and party are required!",
                "danger"
            )

            return redirect("/admin")

        if len(name) > 100 or len(party) > 100:

            flash(
                "Candidate name or party is too long!",
                "danger"
            )

            return redirect("/admin")

        # --------------------------
        # Check Duplicate Candidate
        # --------------------------

        existing_candidate = Candidate.query.filter(
            db.func.lower(Candidate.name) == name.lower()
        ).first()

        if existing_candidate:

            flash(
                "A candidate with this name already exists!",
                "danger"
            )

            return redirect("/admin")

        # --------------------------
        # Get Candidate Photo
        # --------------------------

        photo = request.files.get(
            "photo"
        )

        if not photo or photo.filename == "":

            flash(
                "Candidate photo is required!",
                "danger"
            )

            return redirect("/admin")

        # --------------------------
        # Secure Filename
        # --------------------------

        original_filename = secure_filename(
            photo.filename
        )

        if not allowed_file(original_filename):

            flash(
                "Invalid image format! Only JPG, JPEG, PNG and WEBP files are allowed.",
                "danger"
            )

            return redirect("/admin")

        extension = original_filename.rsplit(
            ".",
            1
        )[1].lower()

        # --------------------------
        # Generate Unique Filename
        # --------------------------

        filename = (
            str(uuid.uuid4())
            + "."
            + extension
        )

        # ==========================
        # Add Candidate to Blockchain
        # ==========================

        try:

            blockchain_tx_hash = add_candidate(
                name,
                party
            )

            print("=" * 60)
            print("CANDIDATE ADDED TO BLOCKCHAIN")
            print(
                "Transaction Hash:",
                blockchain_tx_hash
            )
            print("=" * 60)

        except Exception as e:

            print("=" * 60)
            print("BLOCKCHAIN CANDIDATE ADD ERROR")
            print(e)
            print("=" * 60)

            flash(
                "Candidate could not be added to blockchain.",
                "danger"
            )

            return redirect("/admin")

        # ==========================
        # Verify Blockchain Candidate
        # ==========================

        try:

            blockchain_candidate_count = (
                get_candidate_count()
            )

            if blockchain_candidate_count <= 0:

                raise Exception(
                    "Blockchain candidate count is invalid."
                )

            blockchain_candidate_id = (
                blockchain_candidate_count - 1
            )

            blockchain_candidate = get_candidate(
                blockchain_candidate_id
            )

            # --------------------------
            # Verify Candidate ID
            # --------------------------

            if (
                blockchain_candidate[0]
                != blockchain_candidate_id
            ):

                raise Exception(
                    "Blockchain candidate ID mismatch."
                )

            # --------------------------
            # Verify Candidate Name
            # --------------------------

            if (
                blockchain_candidate[1]
                != name
            ):

                raise Exception(
                    "Blockchain candidate name mismatch."
                )

            # --------------------------
            # Verify Candidate Party
            # --------------------------

            if (
                blockchain_candidate[2]
                != party
            ):

                raise Exception(
                    "Blockchain candidate party mismatch."
                )

        except Exception as e:

            print("=" * 60)
            print(
                "BLOCKCHAIN CANDIDATE VERIFICATION ERROR"
            )
            print(e)
            print("=" * 60)

            flash(
                "Candidate was added to blockchain, but blockchain verification failed. Database was not updated.",
                "danger"
            )

            return redirect("/admin")

        # ==========================
        # Save Candidate Photo
        # ==========================

        upload_folder = os.path.join(
            "static",
            "uploads"
        )

        try:

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            photo_path = os.path.join(
                upload_folder,
                filename
            )

            photo.save(
                photo_path
            )

        except Exception as e:

            print("=" * 60)
            print(
                "CANDIDATE PHOTO SAVE ERROR"
            )
            print(e)
            print(
                "Blockchain Transaction Hash:",
                blockchain_tx_hash
            )
            print("=" * 60)

            flash(
                "Candidate was added to blockchain, but the candidate photo could not be saved. Database was not updated.",
                "danger"
            )

            return redirect("/admin")

        # ==========================
        # Add Candidate to Database
        # ==========================

        try:

            candidate = Candidate(
                name=name,
                party=party,
                photo=filename
            )

            db.session.add(
                candidate
            )

            db.session.commit()

        except Exception as e:

            db.session.rollback()

            # --------------------------
            # Remove Photo
            # --------------------------

            if os.path.exists(
                photo_path
            ):

                try:

                    os.remove(
                        photo_path
                    )

                except Exception as remove_error:

                    print("=" * 60)
                    print(
                        "PHOTO CLEANUP ERROR"
                    )
                    print(remove_error)
                    print("=" * 60)

            print("=" * 60)
            print(
                "CANDIDATE DATABASE SAVE ERROR"
            )
            print(e)
            print(
                "Blockchain Transaction Hash:",
                blockchain_tx_hash
            )
            print("=" * 60)

            flash(
                "Candidate was added to blockchain, but database synchronization failed. Please contact the administrator.",
                "danger"
            )

            return redirect("/admin")

        # ==========================
        # Candidate Add Success
        # ==========================

        flash(
            "Candidate Added Successfully!",
            "success"
        )

        return redirect("/admin")

        # ==========================
    # Dashboard Statistics
    # ==========================

    try:

        candidates = Candidate.query.order_by(
            Candidate.id.asc()
        ).all()

        total_candidates = len(
            candidates
        )

        total_users = User.query.count()

    except Exception as e:

        print("=" * 60)
        print("ADMIN DATABASE STATISTICS ERROR")
        print(e)
        print("=" * 60)

        flash(
            "Unable to load administrator dashboard data.",
            "danger"
        )

        return redirect("/dashboard")

    # ==========================
    # Blockchain Verification
    # ==========================

    blockchain_verified = False

    blockchain_status = False

    blockchain_candidates = []

    blockchain_candidate_count = 0

    total_votes = 0

    try:

        # --------------------------
        # Check Blockchain Connection
        # --------------------------

        if not web3.is_connected():

            raise Exception(
                "Blockchain network is not connected."
            )

        # --------------------------
        # Check Smart Contract
        # --------------------------

        contract_code = web3.eth.get_code(
            contract.address
        )

        if len(contract_code) == 0:

            raise Exception(
                "Smart contract is not deployed."
            )

        blockchain_status = True

        # --------------------------
        # Get Candidate Count
        # --------------------------

        blockchain_candidate_count = (
            get_candidate_count()
        )

        # --------------------------
        # Candidate Count Check
        # --------------------------

        if (
            blockchain_candidate_count
            != total_candidates
        ):

            raise Exception(
                "Blockchain and database candidate counts do not match."
            )

        # --------------------------
        # Read Blockchain Candidates
        # --------------------------

        for i in range(
            blockchain_candidate_count
        ):

            blockchain_candidate = get_candidate(
                i
            )

            # --------------------------
            # Verify Blockchain ID
            # --------------------------

            if blockchain_candidate[0] != i:

                raise Exception(
                    "Blockchain candidate ID mismatch."
                )

            blockchain_candidates.append({
                "id": blockchain_candidate[0],
                "name": blockchain_candidate[1],
                "party": blockchain_candidate[2],
                "votes": blockchain_candidate[3]
            })

        # ==========================
        # Database ↔ Blockchain Check
        # ==========================

        for i in range(
            total_candidates
        ):

            database_candidate = (
                candidates[i]
            )

            blockchain_candidate = (
                blockchain_candidates[i]
            )

            # --------------------------
            # Candidate ID
            # --------------------------

            expected_blockchain_id = (
                database_candidate.id - 1
            )

            if (
                blockchain_candidate["id"]
                != expected_blockchain_id
            ):

                raise Exception(
                    "Candidate ID synchronization mismatch."
                )

            # --------------------------
            # Candidate Name
            # --------------------------

            if (
                database_candidate.name
                != blockchain_candidate["name"]
            ):

                raise Exception(
                    "Candidate name synchronization mismatch."
                )

            # --------------------------
            # Candidate Party
            # --------------------------

            if (
                database_candidate.party
                != blockchain_candidate["party"]
            ):

                raise Exception(
                    "Candidate party synchronization mismatch."
                )

            # --------------------------
            # Vote Count
            # --------------------------

            if (
                database_candidate.votes
                != blockchain_candidate["votes"]
            ):

                raise Exception(
                    "Candidate vote count synchronization mismatch."
                )

        # --------------------------
        # Calculate Total Votes
        # --------------------------

        total_votes = sum(
            candidate["votes"]
            for candidate
            in blockchain_candidates
        )

        blockchain_verified = True

    except Exception as e:

        blockchain_verified = False

        print("=" * 60)
        print("ADMIN BLOCKCHAIN VERIFICATION ERROR")
        print(e)
        print("=" * 60)

    # ==========================
    # Synchronization Warning
    # ==========================

    if not blockchain_status:

        flash(
            "Blockchain network or smart contract is unavailable.",
            "warning"
        )

    elif not blockchain_verified:

        flash(
            "Blockchain and database data are not synchronized. Dashboard statistics are temporarily limited.",
            "warning"
        )

    # ==========================
    # Voter Statistics
    # ==========================

    if blockchain_verified:

        if total_users > 0:

            voting_percentage = round(
                (
                    total_votes
                    / total_users
                ) * 100,
                2
            )

        else:

            voting_percentage = 0

        remaining_voters = (
            total_users
            - total_votes
        )

        if remaining_voters < 0:

            remaining_voters = 0

    else:

        total_votes = 0

        voting_percentage = 0

        remaining_voters = total_users

    # ==========================
    # Election
    # ==========================

    try:

        election = Election.query.first()

    except Exception as e:

        print("=" * 60)
        print("ELECTION STATUS DATABASE ERROR")
        print(e)
        print("=" * 60)

        election = None

    # ==========================
    # Winner
    # ==========================

    winner = None

    tied_candidates = []

    if blockchain_verified and blockchain_candidates:

        highest_votes = max(
            candidate["votes"]
            for candidate
            in blockchain_candidates
        )

        tied_candidates = [
            candidate
            for candidate
            in blockchain_candidates
            if candidate["votes"]
            == highest_votes
        ]

        # Winner is shown only when
        # exactly one candidate has
        # the highest vote count.

        if len(tied_candidates) == 1:

            winner = tied_candidates[0]

    # ==========================
    # Lowest Candidate
    # ==========================

    lowest_candidate = None

    if blockchain_verified and blockchain_candidates:

        lowest_candidate = min(
            blockchain_candidates,
            key=lambda candidate:
            candidate["votes"]
        )

    # ==========================
    # Blockchain Transactions
    # ==========================

    try:

        transactions = Transaction.query.order_by(
            Transaction.id.desc()
        ).all()

    except Exception as e:

        print("=" * 60)
        print("TRANSACTION HISTORY ERROR")
        print(e)
        print("=" * 60)

        transactions = []

        flash(
            "Transaction history could not be loaded.",
            "warning"
        )

    # ==========================
    # Chart Data
    # ==========================

    if blockchain_verified:

        chart_labels = [
            candidate["name"]
            for candidate
            in blockchain_candidates
        ]

        chart_votes = [
            candidate["votes"]
            for candidate
            in blockchain_candidates
        ]

    else:

        # Do not display potentially
        # misleading vote chart data.

        chart_labels = []

        chart_votes = []

    # ==========================
    # Render Admin Page
    # ==========================

    return render_template(
        "admin.html",
        candidates=candidates,
        total_candidates=total_candidates,
        total_users=total_users,
        total_votes=total_votes,
        remaining_voters=remaining_voters,
        voting_percentage=voting_percentage,
        blockchain_status=blockchain_status,
        blockchain_verified=blockchain_verified,
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

@app.route("/delete_candidate/<int:id>", methods=["POST"])
@admin_required
def delete_candidate(id):

    flash(
        "Candidate deletion is disabled to protect blockchain candidate mapping.",
        "warning"
    )

    return redirect("/admin")

# ==========================
# Edit Candidate
# ==========================
# ==========================
# Edit Candidate
# ==========================

@app.route(
    "/edit_candidate/<int:id>",
    methods=["GET", "POST"]
)
@admin_required
def edit_candidate(id):

    candidate = Candidate.query.get_or_404(id)

    flash(
        "Candidate name and party editing is disabled to protect blockchain candidate mapping.",
        "warning"
    )

    return redirect("/admin")

# ==========================
# Start Election
# ==========================

# ==========================
# Start Election
# ==========================

@app.route("/start_election", methods=["POST"])
@admin_required
def start_election():

    try:

        election = Election.query.first()

        if election is None:

            election = Election(
                is_active=False
            )

            db.session.add(election)

        election.is_active = True

        db.session.commit()

        flash(
            "Election Started Successfully!",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print("=" * 60)
        print("START ELECTION ERROR")
        print(e)
        print("=" * 60)

        flash(
            "Election could not be started. Please try again.",
            "danger"
        )

    return redirect("/admin")

# ==========================
# Stop Election
# ==========================

# ==========================
# Stop Election
# ==========================

@app.route("/stop_election", methods=["POST"])
@admin_required
def stop_election():

    try:

        election = Election.query.first()

        if election is None:

            election = Election(
                is_active=False
            )

            db.session.add(election)

        election.is_active = False

        db.session.commit()

        flash(
            "Election Stopped Successfully!",
            "warning"
        )

    except Exception as e:

        db.session.rollback()

        print("=" * 60)
        print("STOP ELECTION ERROR")
        print(e)
        print("=" * 60)

        flash(
            "Election could not be stopped. Please try again.",
            "danger"
        )

    return redirect("/admin")


# ==========================
# Vote
# ==========================

@app.route(
    "/vote",
    methods=["GET", "POST"]
)
@login_required
def vote_page():

    user = db.session.get(
        User,
        session["user_id"]
    )

    # ==========================
    # Check User
    # ==========================

    if user is None:

        session.clear()

        flash(
            "User account not found.",
            "danger"
        )

        return redirect("/login")

    # ==========================
    # Check Election Status
    # ==========================

    election = Election.query.first()

    if election is None or not election.is_active:

        flash(
            "Election is currently closed.",
            "warning"
        )

        return redirect("/dashboard")

    # ==========================
    # Check Previous Vote
    # ==========================

    if user.has_voted:

        flash(
            "You have already voted!",
            "warning"
        )

        return redirect("/dashboard")

    # ==========================
    # Handle Vote Submission
    # ==========================

    if request.method == "POST":

        candidate_id = request.form.get(
            "candidate_id",
            ""
        ).strip()

        # ==========================
        # Validate Candidate ID
        # ==========================

        if not candidate_id.isdigit():

            flash(
                "Invalid candidate selection!",
                "danger"
            )

            return redirect("/vote")

        candidate_id = int(
            candidate_id
        )

        # ==========================
        # Find Candidate in Database
        # ==========================

        candidate = db.session.get(
            Candidate,
            candidate_id
        )

        if candidate is None:

            flash(
                "Candidate not found!",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Map Database ID
        # to Blockchain ID
        # ==========================

        blockchain_candidate_id = (
            candidate_id - 1
        )

        # ==========================
        # Verify Blockchain Candidate
        # ==========================

        try:

            blockchain_candidate = get_candidate(
                blockchain_candidate_id
            )

        except Exception as e:

            print("=" * 60)
            print("BLOCKCHAIN CANDIDATE CHECK ERROR")
            print(e)
            print("=" * 60)

            flash(
                "Unable to verify candidate on the blockchain.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Verify Candidate Mapping
        # ==========================

        if blockchain_candidate[0] != blockchain_candidate_id:

            print("=" * 60)
            print("BLOCKCHAIN CANDIDATE MAPPING ERROR")
            print("Database Candidate ID:", candidate_id)
            print(
                "Blockchain Candidate ID:",
                blockchain_candidate_id
            )
            print(
                "Blockchain Returned ID:",
                blockchain_candidate[0]
            )
            print("=" * 60)

            flash(
                "Candidate verification failed.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Verify Candidate Name
        # ==========================

        if blockchain_candidate[1] != candidate.name:

            print("=" * 60)
            print("BLOCKCHAIN CANDIDATE NAME MISMATCH")
            print("Database:", candidate.name)
            print(
                "Blockchain:",
                blockchain_candidate[1]
            )
            print("=" * 60)

            flash(
                "Candidate verification failed.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Verify Candidate Party
        # ==========================

        if blockchain_candidate[2] != candidate.party:

            print("=" * 60)
            print("BLOCKCHAIN CANDIDATE PARTY MISMATCH")
            print("Database:", candidate.party)
            print(
                "Blockchain:",
                blockchain_candidate[2]
            )
            print("=" * 60)

            flash(
                "Candidate verification failed.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Validate Wallet
        # ==========================

        voter_account = user.wallet_address

        if not voter_account:

            flash(
                "Blockchain wallet not assigned to this user!",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Validate Ethereum Address
        # ==========================

        if not web3.is_address(voter_account):

            flash(
                "Invalid blockchain wallet address.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Convert to Checksum Address
        # ==========================

        try:

            voter_account = web3.to_checksum_address(
                voter_account
            )

        except Exception as e:

            print("=" * 60)
            print("WALLET CHECKSUM ERROR")
            print(e)
            print("=" * 60)

            flash(
                "Invalid blockchain wallet address.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Verify Wallet Exists
        # in Ganache
        # ==========================

        try:

            ganache_accounts = [
                web3.to_checksum_address(account)
                for account in web3.eth.accounts
            ]

        except Exception as e:

            print("=" * 60)
            print("GANACHE ACCOUNT CHECK ERROR")
            print(e)
            print("=" * 60)

            flash(
                "Unable to verify blockchain wallet.",
                "danger"
            )

            return redirect("/vote")

        if voter_account not in ganache_accounts:

            flash(
                "The registered wallet is not available on the blockchain network.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Cast Vote on Blockchain
        # ==========================

        try:

            tx_hash = cast_vote(
                blockchain_candidate_id,
                voter_account
            )

        except Exception as e:

            print("=" * 60)
            print("BLOCKCHAIN VOTE ERROR")
            print(e)
            print("=" * 60)

            flash(
                "Vote could not be recorded on the blockchain. Please try again.",
                "danger"
            )

            return redirect("/vote")

                # ==========================
        # Update Database
        # ==========================

        try:

            # Get the actual vote count
            # from the blockchain
            blockchain_candidate = get_candidate(
                blockchain_candidate_id
            )

            blockchain_vote_count = (
                blockchain_candidate[3]
            )

            # Synchronize database with
            # blockchain vote count
            candidate.votes = (
                blockchain_vote_count
            )

            # Mark voter as voted
            user.has_voted = True

            # Store transaction record
            transaction = Transaction(
                voter_name=user.full_name,
                candidate_name=candidate.name,
                tx_hash=str(tx_hash)
            )

            db.session.add(
                transaction
            )

            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print("=" * 60)
            print("DATABASE VOTE UPDATE ERROR")
            print(e)
            print(
                "Blockchain Transaction Hash:",
                tx_hash
            )
            print("=" * 60)

            flash(
                "Vote was recorded on the blockchain, but database synchronization failed. Please contact the administrator.",
                "danger"
            )

            return redirect("/vote")

        # ==========================
        # Store Vote Information
        # ==========================

        session["tx_hash"] = str(
            tx_hash
        )

        session["candidate_name"] = (
            candidate.name
        )

        flash(
            "Vote Cast Successfully!",
            "success"
        )

        return redirect(
            "/vote_success"
        )

    # ==========================
    # Display Voting Page
    # ==========================

    candidates = Candidate.query.all()

    return render_template(
        "vote.html",
        candidates=candidates
    )


# ==========================
# Vote Success
# ==========================
@app.route("/vote_success")
@login_required
def vote_success():

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
@login_required
def results():

    # ==========================
    # Get Blockchain Candidates
    # ==========================

    try:

        total = get_candidate_count()

    except Exception as e:

        print("=" * 60)
        print("BLOCKCHAIN RESULTS ERROR")
        print(e)
        print("=" * 60)

        flash(
            "Blockchain connection failed. Please try again later.",
            "danger"
        )

        return redirect("/dashboard")

    database_candidates = Candidate.query.all()

    candidates = []

    total_votes = 0

    # ==========================
    # Verify Candidate Count
    # ==========================

    if total != len(database_candidates):

        flash(
            "Blockchain and database candidate data are not synchronized.",
            "danger"
        )

        return redirect("/dashboard")

    # ==========================
    # Build Candidate Results
    # ==========================

    for i in range(total):

        try:

            data = get_candidate(i)

        except Exception as e:

            print("=" * 60)
            print("BLOCKCHAIN CANDIDATE RESULTS ERROR")
            print(e)
            print("=" * 60)

            flash(
                "Unable to retrieve candidate results from the blockchain.",
                "danger"
            )

            return redirect("/dashboard")

        total_votes += data[3]

        candidates.append({
            "id": data[0] + 1,
            "name": data[1],
            "party": data[2],
            "votes": data[3],
            "photo": database_candidates[i].photo
        })

    # ==========================
    # Blockchain Verification
    # ==========================

    blockchain_verified = True

    for i in range(total):

        blockchain_votes = candidates[i]["votes"]

        database_votes = database_candidates[i].votes

        if blockchain_votes != database_votes:

            blockchain_verified = False

            print("=" * 60)
            print("RESULTS BLOCKCHAIN DATABASE MISMATCH")
            print(
                "Candidate:",
                candidates[i]["name"]
            )
            print(
                "Blockchain Votes:",
                blockchain_votes
            )
            print(
                "Database Votes:",
                database_votes
            )
            print("=" * 60)

            break

    # ==========================
    # Winner & Runner-up
    # ==========================

    winner = None

    runner_up = None

    tie = False

    tied_candidates = []

    if candidates:

        sorted_candidates = sorted(
            candidates,
            key=lambda x: x["votes"],
            reverse=True
        )

        highest_votes = sorted_candidates[0]["votes"]

        # Find all candidates with highest votes

        tied_candidates = [
            candidate
            for candidate in sorted_candidates
            if candidate["votes"] == highest_votes
        ]

        # Check for tie

        if len(tied_candidates) > 1:

            tie = True

            winner = None

        else:

            winner = sorted_candidates[0]

            if len(sorted_candidates) >= 2:

                runner_up = sorted_candidates[1]

    # ==========================
    # Total Registered Users
    # ==========================

    total_users = User.query.count()

    # ==========================
    # Voting Percentage
    # ==========================

    voting_percentage = 0

    if total_users > 0:

        voting_percentage = round(
            (total_votes / total_users) * 100,
            2
        )

    # ==========================
    # Election Status
    # ==========================

    election = Election.query.first()

    election_status = "Closed"

    if election and election.is_active:

        election_status = "Open"

    # ==========================
    # Winning Margin
    # ==========================

    winning_margin = 0

    if winner and runner_up:

        winning_margin = (
            winner["votes"]
            - runner_up["votes"]
        )

    # ==========================
    # Chart Data
    # ==========================

    chart_labels = [
        candidate["name"]
        for candidate in candidates
    ]

    chart_votes = [
        candidate["votes"]
        for candidate in candidates
    ]

    # ==========================
    # Render Results
    # ==========================

    return render_template(
        "results.html",
        candidates=candidates,
        total_votes=total_votes,
        winner=winner,
        runner_up=runner_up,
        chart_labels=chart_labels,
        chart_votes=chart_votes,
        total_users=total_users,
        tie=tie,
        tied_candidates=tied_candidates,
        voting_percentage=voting_percentage,
        election_status=election_status,
        winning_margin=winning_margin,
        blockchain_verified=blockchain_verified
    )

@app.route("/transactions")
@admin_required
def transactions():

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

@app.route("/reset_election", methods=["POST"])
@admin_required
def reset_election():

    # ==========================
    # Reset Blockchain Election
    # ==========================

    try:

        blockchain_tx_hash = reset_blockchain_election()

        print("=" * 60)
        print("BLOCKCHAIN ELECTION RESET")
        print("Transaction Hash:", blockchain_tx_hash)
        print("=" * 60)

    except Exception as e:

        print("=" * 60)
        print("BLOCKCHAIN RESET ERROR")
        print(e)
        print("=" * 60)

        flash(
            "Blockchain reset failed. Database was not reset.",
            "danger"
        )

        return redirect("/admin")

    # ==========================
    # Reset Database Election
    # ==========================

    try:

        # Reset Candidate Votes
        candidates = Candidate.query.all()

        for candidate in candidates:
            candidate.votes = 0

        # Reset Users
        users = User.query.all()

        for user in users:
            user.has_voted = False

        # Delete Transaction History
        Transaction.query.delete()

        # Close Election
        election = Election.query.first()

        if election:
            election.is_active = False

        # Save Database Changes
        db.session.commit()

    except Exception as e:

        db.session.rollback()

        print("=" * 60)
        print("DATABASE RESET ERROR")
        print(e)
        print("Blockchain Transaction Hash:", blockchain_tx_hash)
        print("=" * 60)

        flash(
            "Blockchain election was reset, but database synchronization failed. Please contact the administrator.",
            "danger"
        )

        return redirect("/admin")

    # ==========================
    # Reset Successful
    # ==========================

    flash(
        "Election Reset Successfully on Blockchain and Database!",
        "success"
    )

    return redirect("/admin")

@app.route("/export_pdf")
@admin_required
def export_pdf():

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
@admin_required
def export_excel():

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
@admin_required
def download_report():

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
    app.run(
        debug=False
    )