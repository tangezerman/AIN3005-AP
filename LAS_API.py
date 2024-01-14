from flask import Flask, jsonify, request
from kafka import KafkaProducer
import json
import hashlib
import jwt
import datetime
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB setup
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['library_database']
users_collection = db['users']
books_collection = db['books']

# Kafka Producer setup
producer = KafkaProducer(bootstrap_servers=['localhost:9092'],
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

SECRET_KEY = "your-very-secure-and-secret-key"

class Book:
    def __init__(self, name: str, author: str, btype: str) -> None:
        self.client = MongoClient('mongodb://localhost:27017/')  # connect to MongoDB
        self.db = self.client['library_database']  # use or create the database
        self.collection = self.db['books']  # use or create the collection
        existing_book = self.collection.find_one({'name': name, 'author': author})
        if existing_book:
            self.book_id = existing_book['_id']
            print(f"Book '{name}' by '{author}' already exists in the library.")
        else:
            self.book_id = self.collection.insert_one({
                'name': name,
                'author': author,
                'btype': btype,
                'reserved': False,
                'lent_to': None,
                'due': None,
                'extensions': 0
            }).inserted_id    

    def get_book_info(self):
        return self.collection.find_one({'_id': self.book_id})

    @classmethod
    def find_by_id(cls, book_id):
        client = MongoClient('mongodb://localhost:27017/')
        db = client['library_database']
        collection = db['books']
        book_data = collection.find_one({'_id': book_id})

        if book_data:
            return cls(book_data['name'], book_data['author'], book_data['btype'])
        return None

    @property
    def name(self) -> str:
        return self.get_book_info()['name']

    @property
    def author(self) -> str:
        return self.get_book_info()['author']

    @property
    def btype(self) -> str:
        return self.get_book_info()['btype']

    @property
    def reserved(self) -> bool:
        return self.get_book_info()['reserved']

    @property
    def lent_to(self) -> Optional[str]:
        return self.get_book_info()['lent_to']

    @property
    def due(self) -> Optional[datetime]:
        due_info = self.get_book_info()['due']
        if due_info:
            return datetime.strptime(due_info, "%Y-%m-%d %H:%M:%S")
        else:
            return None

    def reserve_book(self, borrower: str, borrower_type: str) -> bool:
        book_info = self.get_book_info()
        if book_info['reserved'] or (book_info['btype'] in ['textbook', 'periodical'] and borrower_type != 'faculty'):
            return False
        lending_period = 40 if borrower_type == 'faculty' else 15
        due_date = datetime.now() + timedelta(days=lending_period)
        self.collection.update_one({'_id': self.book_id}, {'$set': {'reserved': True, 'lent_to': borrower, 'due': due_date}})
        return True

    def extend_due_date(self, user_type: str) -> bool:
        book_info = self.get_book_info()
        extension_limit = 5 if user_type == 'faculty' else 3
        if book_info['extensions'] >= extension_limit or book_info['due'] is None or datetime.now() > book_info['due']:
            return False
        extension_days = 30 if book_info['btype'] == 'textbook' else 15
        new_due_date = book_info['due'] + timedelta(days=extension_days)
        self.collection.update_one({'_id': self.book_id}, {'$set': {'due': new_due_date, 'extensions': book_info['extensions'] + 1}})
        return True

    def return_book(self) -> None:
        self.collection.update_one({'_id': self.book_id}, {'$set': {'reserved': False, 'lent_to': None, 'due': None, 'extensions': 0}})

    def __str__(self) -> str:
        book_info = self.get_book_info()
        return f"{book_info['name']} by {book_info['author']}"


    def __str__(self) -> str:
        book_info = self.get_book_info()
        return f"{book_info['name']} by {book_info['author']}"




class User:
    def __init__(self, name: str, user_type: str) -> None:
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['library_database']
        self.collection = self.db['users']

        # Check if the user already exists
        existing_user = self.collection.find_one({'name': name, 'user_type': user_type})
        if existing_user:
            self.user_id = existing_user['_id']
            print(f"User '{name}' of type '{user_type}' already exists.")
        else:
            self.user_id = self.collection.insert_one({
                'name': name,
                'user_type': user_type,
                'books_borrowed': []
            }).inserted_id
        self.MAX_BORROW_LIMIT = 5 if user_type == 'faculty' else 3




    def get_user_info(self):
        return self.collection.find_one({'_id': self.user_id})

    @classmethod
    def find_by_id(cls, user_id):
        client = MongoClient('mongodb://localhost:27017/')
        db = client['library_database']
        collection = db['users']
        user_data = collection.find_one({'_id': user_id})

        if user_data:
            return cls(user_data['name'], user_data['user_type'], SECRET_KEY)
        return None



    @property
    def name(self) -> str:
        return self.get_user_info()['name']

    @property
    def books_borrowed(self) -> List[str]:  # Now stores a list of book IDs
        return self.get_user_info()['books_borrowed']

    @property
    def user_type(self) -> str:
        return self.get_user_info()['user_type']

    def borrow_book(self, book: Book) -> None:
        if len(self.books_borrowed) < self.MAX_BORROW_LIMIT and book.reserve_book(self.name, self.user_type):
            self.collection.update_one({'_id': self.user_id}, {'$push': {'books_borrowed': book.book_id}})
            print(f"{self.name} has borrowed {book}.")
        else:
            print(f"{self.name} cannot borrow {book}.")

    def return_book(self, book: Book) -> None:
        if book.book_id in self.books_borrowed:
            book.return_book()
            self.collection.update_one({'_id': self.user_id}, {'$pull': {'books_borrowed': book.book_id}})
            print(f"{self.name} has returned {book}.")
        else:
            print(f"{self.name} did not borrow {book}.")

    def __str__(self) -> str:
        user_info = self.get_user_info()
        return f"User: {user_info['name']}, Type: {user_info['user_type']}"




class Library:
    def __init__(self) -> None:
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['library_database']
        self.books_collection = self.db['books']
        self.users_collection = self.db['users']

    def add_book(self, book: Book) -> None:
        # The Book instance will handle adding itself to the MongoDB
        print(f"Added {book} to the library.")

    def search_books(self, title: Optional[str] = None, author: Optional[str] = None) -> None:
        query = {}
        if title:
            query['name'] = title
        if author:
            query['author'] = author

        for book in self.books_collection.find(query):
            print(f"{book['name']} by {book['author']}")

    def list_all_books(self) -> None:
        print("Library Books:")
        for book in self.books_collection.find():
            print(f"{book['name']} by {book['author']}")

    def extend_due_date(self, user: User, book: Book) -> None:
        # Assuming User and Book classes have been refactored to use MongoDB
        if book.book_id in user.books_borrowed and book.extend_due_date(user.user_type):
            print(f"The due date for {book} has been extended.")
        else:
            print(f"Cannot extend due date for {book}.")

    def calculate_fine(self, book: Book) -> int:
        if book.due is not None and datetime.now() > book.due:
            overdue_days = (datetime.now() - book.due).days
            fine = 10 if overdue_days <= 7 else 20 * (overdue_days - 7) + 10
            return fine
        return 0

    def check_fines(self, user: User) -> None:
        total_fine = 0
        for book_id in user.books_borrowed:
            book = Book.find_by_id(book_id)  # Assuming a method in Book to find by ID
            fine = self.calculate_fine(book)
            if fine > 0:
                print(f"{user.name} has an overdue fine of {fine} Turkish Lira for {book}.")
                total_fine += fine
        if total_fine > 0:
            print(f"Total fine for {user.name} is {total_fine} Turkish Lira.")
        else:
            print(f"{user.name} has no fines.")


@app.route('/user/borrow_book', methods=['POST'])
def borrow_book():
    data = request.json
    token = data['token']
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    user_id = payload['user_id']
    book_id = data['book_id']
    user = User.find_by_id(user_id)  # Implement this method in User class
    book = Book.find_by_id(book_id)  # Implement this method in Book class

    if user.borrow_book(book):
        producer.send('library_topic', {'action': 'borrow_book', 'user_id': user_id, 'book_id': book_id})
        return jsonify({"message": "Book borrowed successfully"}), 200
    else:
        return jsonify({"message": "Cannot borrow book"}), 400

@app.route('/user/extend_due_date', methods=['POST'])
def extend_due_date():
    data = request.json
    token = data['token']
    book_id = data['book_id']
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    user_id = payload['user_id']
    user = User.find_by_id(user_id)  
    book = Book.find_by_id(book_id)  

    if book and user and book.book_id in user.books_borrowed:
        if book.extend_due_date(user.user_type):
            producer.send('library_topic', {'action': 'extend_due_date', 'user_id': user_id, 'book_id': book_id})
            return jsonify({"message": "Due date extended successfully"}), 200
        else:
            return jsonify({"message": "Cannot extend due date"}), 400
    else:
        return jsonify({"message": "Invalid user or book ID"}), 404

@app.route('/book/add', methods=['POST'])
def add_book():
    data = request.json
    name = data.get('name')
    author = data.get('author')
    btype = data.get('btype')

    if not all([name, author, btype]):
        return jsonify({"message": "Missing book information"}), 400

    book = Book(name, author, btype)
    
    # Check if the book was successfully added (i.e., not a duplicate)
    existing_book = books_collection.find_one({'_id': book.book_id})
    if existing_book:
        return jsonify({"message": "Book already exists"}), 409
    else:
        # Optionally, send a message to Kafka for logging or further processing
        producer.send('library_topic', {'action': 'add_book', 'book_id': book.book_id})
        return jsonify({"message": "Book added successfully", "book_id": book.book_id}), 201

@app.route('/user/return_book', methods=['POST'])
def return_book():
    data = request.json
    token = data.get('token')
    book_id = data.get('book_id')

    if not token or not book_id:
        return jsonify({"message": "Missing token or book ID"}), 400

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    user_id = payload['user_id']
    user = User.find_by_id(user_id)
    book = Book.find_by_id(book_id)

    if not user or not book:
        return jsonify({"message": "Invalid user or book ID"}), 404

    if book.book_id not in user.books_borrowed:
        return jsonify({"message": "This book is not borrowed by the user"}), 400

    # Logic to return the book
    user.return_book(book)
    book.return_book()  # Update the book's status in the database

    # Optionally, send a message to Kafka for logging or further processing
    producer.send('library_topic', {'action': 'return_book', 'user_id': user_id, 'book_id': book_id})
    return jsonify({"message": "Book returned successfully"}), 200

@app.route('/user/check_fines', methods=['POST'])
def check_fines():
    data = request.json
    token = data.get('token')

    if not token:
        return jsonify({"message": "Missing token"}), 400

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    user_id = payload['user_id']
    user = User.find_by_id(user_id)

    if not user:
        return jsonify({"message": "Invalid user ID"}), 404

    fines = user.calculate_fines()

    if fines:
        return jsonify({"message": f"{user.name} has an overdue fine of {fines} Turkish Lira"}), 200
    else:
        return jsonify({"message": f"{user.name} has no fines."}), 200

