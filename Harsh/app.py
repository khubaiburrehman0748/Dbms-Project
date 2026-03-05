from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from backend import RailwayBackend

# Initialize Flask App
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Initialize Database
db = RailwayBackend()

# --- ROUTE: Serve the HTML File ---
@app.route('/')
def index():
    return send_file('index.html')

# --- API: User Authentication ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if db.register_user(data):
        return jsonify({"success": True, "message": "Registration Successful"})
    return jsonify({"success": False, "message": "Username/Email already exists or Database Error"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = db.login_user(data['username'], data['password'], data.get('role'))
    if user:
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False, "message": "Invalid Credentials"}), 401

# --- API: Train Management ---
@app.route('/api/trains', methods=['GET'])
def get_trains():
    trains = db.get_all_trains()
    return jsonify(trains)

@app.route('/api/trains/add', methods=['POST'])
def add_train():
    data = request.json
    if db.add_train(data):
        return jsonify({"success": True, "message": "Train Added Successfully"})
    return jsonify({"success": False, "message": "Failed to add train (Check server logs)"}), 400

@app.route('/api/trains/edit/<int:train_id>', methods=['POST', 'PUT'])
def edit_train(train_id):
    data = request.json
    if db.edit_train(train_id, data):
        return jsonify({"success": True, "message": "Train Edited Successfully"})
    return jsonify({"success": False, "message": "Failed to edit train (Check server logs)"}), 400


@app.route('/api/trains/delete/<int:train_id>', methods=['DELETE'])
def delete_train(train_id):
    if db.delete_train(train_id):
        return jsonify({"success": True, "message": "Train Deleted"})
    return jsonify({"success": False, "message": "Failed to delete train"}), 400

# --- API: Booking & PNR ---
@app.route('/api/book', methods=['POST'])
def book_ticket():
    data = request.json
    if db.book_ticket(data):
        return jsonify({"success": True, "message": "Booking Confirmed"})
    return jsonify({"success": False, "message": "Booking Failed (Train Full?)"}), 400

@app.route('/api/bookings/<int:user_id>', methods=['GET'])
def get_bookings(user_id):
    bookings = db.get_user_bookings(user_id)
    return jsonify(bookings)

@app.route('/api/trains/<int:train_id>/bookings', methods=['GET'])
def get_train_bookings(train_id):
    bookings = db.get_train_bookings(train_id)
    return jsonify(bookings)

@app.route('/api/pnr/<string:pnr>', methods=['GET'])
def check_pnr(pnr):
    booking = db.get_booking_by_pnr(pnr)
    if booking:
        return jsonify({"success": True, "data": booking})
    return jsonify({"success": False, "message": "PNR Not Found"})

# --- API: Admin Stats ---
@app.route('/api/users', methods=['GET'])
def get_users():
    users = db.get_all_users()
    return jsonify(users)

if __name__ == '__main__':
    print("Server is running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)