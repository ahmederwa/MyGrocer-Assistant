import os
import openai
import time
from flask import Flask, request, jsonify, session
from packaging import version
from functions import check_item_availability, manage_cart, process_checkout
from prompts import get_welcome_message, get_cart_prompt, get_checkout_prompt

# Version check
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {openai.__version__} is less than the required version 1.1.1")
else:
    print("OpenAI version is compatible.")

# Initialize Flask and OpenAI client
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key for session management
openai.api_key = os.getenv('OPENAI_API_KEY')

# Routes

@app.route('/')
def welcome():
    # Start the conversation by greeting the user
    session.clear()  # Clear any previous session data
    return jsonify({
        "message": get_welcome_message(),
        "next_action": "ask_for_item"
    })

@app.route('/item-check', methods=['POST'])
def item_check():
    # Check item availability
    item_name = request.json.get('item_name')
    availability = check_item_availability(item_name)

    # Use OpenAI to generate a response based on the availability check
    openai_response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"The user asked for {item_name}. Availability: {availability}. How would you respond?",
        max_tokens=150
    )
    response_text = openai_response.choices[0].text.strip()

    # Store item in session for cart management
    session['last_item'] = {"name": item_name, "availability": availability}

    return jsonify({
        "item_name": item_name,
        "availability": availability,
        "response": response_text,
        "next_action": "ask_for_cart"
    })

@app.route('/cart', methods=['POST'])
def cart():
    # Manage the shopping cart (add/view)
    action = request.json.get('action')
    item_name = request.json.get('item_name', None)
    quantity = request.json.get('quantity', None)

    cart_status = manage_cart(action, item_name, quantity)

    # Generate a response using OpenAI based on the cart status
    openai_response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"The user {action} {quantity} of {item_name} to the cart. Current cart status: {cart_status}. How would you respond?",
        max_tokens=150
    )
    response_text = openai_response.choices[0].text.strip()

    return jsonify({
        "cart_status": cart_status,
        "response": response_text,
        "next_action": "ask_for_checkout"
    })

@app.route('/checkout', methods=['POST'])
def checkout():
    # Handle the checkout process
    delivery_address = request.json.get('delivery_address')
    phone_number = request.json.get('phone_number')
    payment_method = request.json.get('payment_method')

    order_summary, order_number = process_checkout(delivery_address, phone_number, payment_method)

    # Generate a response using OpenAI based on the order summary
    openai_response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"The user is checking out with the following order summary: {order_summary}. Order number: {order_number}. How would you respond?",
        max_tokens=150
    )
    response_text = openai_response.choices[0].text.strip()

    return jsonify({
        "order_summary": order_summary,
        "order_number": order_number,
        "response": response_text,
        "message": "Thank you for your order!"
    })

# Error handling route (optional, for robustness)
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "An internal error occurred. Please try again later."}), 500

if __name__ == '__main__':
    app.run(debug=True)
