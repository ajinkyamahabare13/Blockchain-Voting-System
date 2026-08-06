from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    wallet_address = db.Column(db.String(200), nullable=True)

    has_voted = db.Column(db.Boolean, default=False)

    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User {self.full_name}>"


class Candidate(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    party = db.Column(db.String(100), nullable=False)

    photo = db.Column(db.String(255))

    votes = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<Candidate {self.name}>"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    voter_name = db.Column(db.String(100))

    candidate_name = db.Column(db.String(100))

    tx_hash = db.Column(db.String(200))

    timestamp = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

class Election(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    is_active = db.Column(db.Boolean, default=False)