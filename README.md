# AIN3005-AP
This is the term project for AIN3005.

# Overview

## System Architecture Overview

1. **Flask Web Server**: Serves as the backbone of the LAS, handling HTTP requests and responses.
2. **MongoDB Database**: Stores all data related to books and users.
3. **Apache Kafka**: Used for messaging and logging activities.

## Database Schema

### Books Collection:
- `name`: Title of the book (String).
- `author`: Author of the book (String).
- `btype`: Type of the book (e.g., textbook, periodical) (String).
- `reserved`: Indicates if the book is currently reserved (Boolean).
- `lent_to`: ID of the user who borrowed the book (String, Optional).
- `due`: Due date for the borrowed book (Date, Optional).
- `extensions`: The number of times the due date has been extended (Number).

### Users Collection:
- `name`: Name of the user (String).
- `user_type`: Type of the user (e.g., faculty, student) (String).
- `books_borrowed`: List of IDs of books borrowed by the user (Array of Strings).

## Dependencies

- Flask, pymongo, kafka-python, PyJWT, hashlib, datetime. Can be installed with ``````pip install -r requirements.txt``````

# API Endpoints

## Add Book (`/book/add` - POST)

Adds a new book to the library.
Returns success or error message.

## Borrow Book (`/user/borrow_book` - POST)

Allows borrowing of a book.
Returns success or error message.

## Extend Due Date (`/user/extend_due_date` - POST)

Extends the due date of a borrowed book.
Returns success or error message.

## Return Book (`/user/return_book` - POST)

Allows returning of a borrowed book.
Returns success or error message.

## Check Fines (`/user/check_fines` - POST)

Checks for any outstanding fines.
Returns the amount of fine or no fines message.
