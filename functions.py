import PyPDF2
import json
import requests
import os
from flask import session

# Airtable API Key and Base URL
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_URL = "https://api.airtable.com/v0/appeKTAISZxBzJiom/Imported%20table"

# Function to check item availability
def check_item_availability(item_name):
    try:
        with open('roastery.pdf', 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if item_name.lower() in text.lower():
                    return "Available"
        return "Not Available"
    except Exception as e:
        print(f"Error checking item availability: {e}")
        return "Error checking availability"

# Function to manage the shopping cart
def manage_cart(action, item_name=None, quantity=None):
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    if action == 'add' and item_name and quantity:
        if item_name in cart:
            cart[item_name] += quantity
        else:
            cart[item_name] = quantity
        session['cart'] = cart
        return f"Added {quantity} of {item_name} to your cart."

    elif action == 'view':
        return cart

    elif action == 'remove' and item_name:
        if item_name in cart:
            del cart[item_name]
            session['cart'] = cart
            return f"Removed {item_name} from your cart."
        else:
            return f"{item_name} not found in your cart."

    else:
        return "Invalid cart action."

# Function to process the checkout
def process_checkout(delivery_address, phone_number, payment_method):
    cart = session.get('cart', {})
    if not cart:
        return "Your cart is empty.", None

    total_amount = sum([calculate_price(item, quantity) for item, quantity in cart.items()])
    order_summary = {
        "contact_name": session.get('user_name', 'Customer'),
        "cart_details": [f"{quantity} of {item}" for item, quantity in cart.items()],
        "total": total_amount,
        "phone": phone_number,
        "delivery_address": delivery_address,
        "payment": payment_method.capitalize()
    }

    # Send the order details to Airtable
    try:
        airtable_response = send_order_to_airtable(order_summary)
        if airtable_response.status_code == 200:
            order_number = airtable_response.json().get('id')
            return order_summary, order_number
        else:
            print(f"Failed to send order to Airtable: {airtable_response.text}")
            return "Error processing order", None
    except Exception as e:
        print(f"Error processing checkout: {e}")
        return "Error processing order", None

# Helper function to send order details to Airtable
def send_order_to_airtable(order_summary):
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "records": [
            {
                "fields": {
                    "Customer Name": order_summary["contact_name"],
                    "Contact Details": order_summary["phone"],
                    "Address": order_summary["delivery_address"],
                    "Basket Items": ", ".join(order_summary["cart_details"]),
                    "Payment (Card/Cash)": order_summary["payment"],
                    "Order Status": "New"  # Always set to "New"
                }
            }
        ]
    }
    response = requests.post(AIRTABLE_BASE_URL, headers=headers, json=data)
    return response

# Refined function to calculate price based on item and quantity
def calculate_price(item_name, quantity):
    try:
        with open('roastery.pdf', 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                lines = text.splitlines()
                for line in lines:
                    if item_name.lower() in line.lower():
                        # Assuming the price is mentioned alongside the item name in the format "Item Name - Price AED"
                        parts = line.split('-')
                        if len(parts) == 2:
                            price_str = parts[1].strip().replace('AED', '').strip()
                            try:
                                price = float(price_str)
                                return price * quantity
                            except ValueError:
                                continue
        return 0  # Return 0 if the item is not found or price cannot be determined
    except Exception as e:
        print(f"Error calculating price: {e}")
        return 0
